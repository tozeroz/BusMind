<!--
  文件：src/modules/map/components/BusMap.vue
  用途：实现地图业务模块中的地图展示与交互组件。
  存放内容：地图实例、图层、站点线路数据以及地图交互代码。
  实现功能：集中实现公交地图渲染、选中、高亮、定位和数据刷新能力。
-->
<template>
  <div class="bus-map-wrapper">
    <div ref="mapContainer" class="bus-map"></div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import maplibregl from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import 'maplibre-gl/dist/maplibre-gl.css'

import { getMapLines, getMapStations, getRoadSegments } from '@/api/map'
import { createProtomapsStyle } from '@/modules/map/constants/map-style'
import { PRIORITY_BUS_STOP_CODES } from '@/modules/map/constants/priority-stops'

const emit = defineEmits(['select-stop', 'select-route', 'load-error', 'initial-data-loaded'])

const mapContainer = ref(null)
let map = null
let pmtilesProtocol = null
let busStops = []
let busStopsGeoJSON = {
  type: 'FeatureCollection',
  features: []
}
let busRoutesGeoJSON = {
  type: 'FeatureCollection',
  features: []
}
let visibleLineIds = new Set()
let busRoutesLoaded = false
let routesLoadPromise = null
let isStopBoundsFitted = false
let selectedStopForRoutes = null
let selectedStopFeatureId = null
let areRoutesVisible = false

const emptyFeatureCollection = {
  type: 'FeatureCollection',
  features: []
}

const mapDataCache = globalThis.__busmindMapDataCache || {
  stops: null,
  routes: null,
  stopsPromise: null,
  routesPromise: null
}
globalThis.__busmindMapDataCache = mapDataCache

const routeRed = '#e11d2e'
const routeMuted = '#4f8fc0'
const routePalette = ['#FDE14E', '#FDE14E', '#F58329', '#BE9106', '#D6CB00', '#5d9eb7', '#8cb6c6', '#72c0cf', '#5798d0']
const routeColorExpression = ['coalesce', ['get', 'display_color'], routeMuted]
const routeBg = '#ffffff'
const stopFill = '#e11d2e'
const stopDefaultFill = '#2f80ed'
const stopStroke = '#e11d2e'
const stopMutedStroke = '#e11d2e'
const stopPriorityColorExpression = ['case', ['boolean', ['get', 'is_priority_stop'], false], stopFill, stopDefaultFill]
const stopsOpacityByZoom = ['interpolate', ['linear'], ['zoom'], 9, 1, 15, 1]
const stopsDimmedOpacityByZoom = ['interpolate', ['linear'], ['zoom'], 9, 0.3, 15, 0.3]
const stopLabelsOpacityByZoom = ['interpolate', ['linear'], ['zoom'], 15, 1, 16, 1, 17, 1]
const stopLabelsDimmedOpacityByZoom = ['interpolate', ['linear'], ['zoom'], 15, 0.3, 16, 0.3, 17, 0.3]

function isRetryableError(error) {
  // Network-level failures (no response received) are worth retrying.
  if (!error?.response) return true
  // 5xx may be transient (overload, gateway hiccup). 4xx is a caller mistake —
  // retrying just multiplies the noise and the server load.
  const status = error.response.status
  return status >= 500 && status < 600
}

async function runWithRetry(fn, attempts = 3, delayMs = 400) {
  let lastError = null
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await fn()
    } catch (error) {
      lastError = error
      if (attempt >= attempts) break
      if (!isRetryableError(error)) break
      await new Promise((resolve) => setTimeout(resolve, delayMs * attempt))
    }
  }
  throw lastError
}

function getSource(sourceId) {
  return map && map.getSource(sourceId)
}

function setSourceData(sourceId, data) {
  const source = getSource(sourceId)
  if (source) source.setData(data)
}

function setLayerPaintProperty(layerId, property, value) {
  if (map && map.getLayer(layerId)) map.setPaintProperty(layerId, property, value)
}

function setStopsDimmed(isDimmed) {
  setLayerPaintProperty('stops', 'circle-opacity', isDimmed ? stopsDimmedOpacityByZoom : stopsOpacityByZoom)
  setLayerPaintProperty('stops-detail', 'circle-opacity', isDimmed ? ['interpolate', ['linear'], ['zoom'], 13.5, 0, 14.5, 0.18, 17, 0.28] : ['interpolate', ['linear'], ['zoom'], 13.5, 0, 14.5, 0.95])
  setLayerPaintProperty('stop-labels', 'text-opacity', isDimmed ? stopLabelsDimmedOpacityByZoom : stopLabelsOpacityByZoom)
}
function setSelectedStopState(stopId) {
  if (!map || !map.getSource('stops')) return

  if (selectedStopFeatureId !== null) {
    map.setFeatureState({ source: 'stops', id: String(selectedStopFeatureId) }, { selected: false })
  }

  selectedStopFeatureId = stopId === undefined || stopId === null ? null : String(stopId)

  if (selectedStopFeatureId !== null) {
    map.setFeatureState({ source: 'stops', id: selectedStopFeatureId }, { selected: true })
  }
}

function createFeatureCollection(features) {
  return {
    type: 'FeatureCollection',
    features: features || []
  }
}

function coordinatesMatch(first, second) {
  return Math.abs(first[0] - second[0]) < 0.0002 && Math.abs(first[1] - second[1]) < 0.0002
}

function routeStopFeatures(routeCoordinates) {
  const features = []

  busStopsGeoJSON.features.forEach((feature) => {
    const stopCoordinate = feature.geometry.coordinates
    const isOnRoute = routeCoordinates.some((coordinate) => coordinatesMatch(coordinate, stopCoordinate))

    if (isOnRoute) features.push(feature)
  })

  return features
}

function normalizeRouteValues(routes) {
  const normalizeItems = (value) => {
    if (Array.isArray(value)) return value.flatMap((item) => normalizeItems(item))
    if (value === undefined || value === null) return []

    const text = String(value).trim()
    if (!text) return []

    if (text.startsWith('[') && text.endsWith(']')) {
      try {
        const parsed = JSON.parse(text)
        return normalizeItems(parsed)
      } catch {
        // Fall through to delimiter splitting for loosely formatted arrays.
      }
    }

    return text
      .replace(/[\[\]"']/g, '')
      .split(/[|,\/]/)
      .map((item) => item.trim())
      .filter(Boolean)
  }

  return new Set(normalizeItems(routes).map((item) => String(item).toLowerCase()))
}
function routeFeatureMatchesValues(feature, values) {
  if (!values.size) return false

  const properties = feature.properties || {}
  const candidates = [
    properties.line_id,
    properties.line_name,
    properties.line_code,
    properties.service_no
  ]

  return candidates.some((item) => values.has(String(item || '').toLowerCase()))
}

function resolveStop(stopOrId) {
  if (stopOrId === undefined || stopOrId === null) return null

  const stopId = typeof stopOrId === 'object'
    ? (stopOrId.stop_id ?? stopOrId.station_id ?? stopOrId.id)
    : stopOrId
  const knownStop = busStops.find((item) => String(item.stop_id) === String(stopId))

  if (typeof stopOrId === 'object') {
    return knownStop ? { ...knownStop, ...stopOrId } : stopOrId
  }
  return knownStop || null
}

function stopCoordinate(stop) {
  const lng = Number(stop?.lng ?? stop?.longitude)
  const lat = Number(stop?.lat ?? stop?.latitude)
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null
  return [lng, lat]
}

function routeFeatureContainsStop(feature, stop) {
  const coordinates = feature.geometry?.coordinates || []
  const coordinate = stopCoordinate(stop)
  if (!coordinate) return false
  return coordinates.some((routeCoordinate) => coordinatesMatch(routeCoordinate, coordinate))
}

function reachableRouteFeatures(stop) {
  const resolvedStop = resolveStop(stop)
  if (!resolvedStop) return []

  const routeValues = normalizeRouteValues([...(resolvedStop.passing_routes || []), ...(resolvedStop.line_ids || [])])
  const matchedByRoute = busRoutesGeoJSON.features.filter((feature) => routeFeatureMatchesValues(feature, routeValues))
  const matchedAndPassing = matchedByRoute.filter((feature) => routeFeatureContainsStop(feature, resolvedStop))

  if (matchedAndPassing.length) return matchedAndPassing

  const matchedByCoordinate = busRoutesGeoJSON.features.filter((feature) => routeFeatureContainsStop(feature, resolvedStop))
  if (matchedByCoordinate.length) return matchedByCoordinate

  return matchedByRoute
}

function findRouteFeature(routeId) {
  const id = Number(routeId)
  return busRoutesGeoJSON.features.find((feature) => {
    return Number(feature.id) === id || Number(feature.properties.line_id) === id
  })
}

function findStopFeature(stopId) {
  return busStopsGeoJSON.features.find((feature) => String(feature.properties.stop_id) === String(stopId))
}

function getStopRoutes(stopId) {
  const stop = resolveStop(stopId)
  const stopFeature = findStopFeature(stop?.stop_id ?? stopId)
  if (!stopFeature) return []
  if (!stop) return []
  return reachableRouteFeatures(stop)
}

function clearSelection() {
  selectedStopForRoutes = null
  setSelectedStopState(null)
  setStopsDimmed(false)
  setSourceData('routes', emptyFeatureCollection)
  setSourceData('routes-path', emptyFeatureCollection)
  setSourceData('stops-highlight', emptyFeatureCollection)
  setSourceData('stops-highlight-selected', emptyFeatureCollection)
}

function highlightRoute(feature, options = {}) {
  const preservedStopId = options.preserveStopId ?? null
  const preservedStopFeature = preservedStopId !== null
    ? findStopFeature(preservedStopId)
    : null

  selectedStopForRoutes = null
  setSelectedStopState(preservedStopId)
  setStopsDimmed(true)
  const routeCoordinates = feature.geometry.coordinates
  setSourceData('routes', emptyFeatureCollection)
  setSourceData('routes-path', createFeatureCollection([feature]))
  setSourceData('stops-highlight', createFeatureCollection(routeStopFeatures(routeCoordinates)))
  setSourceData(
    'stops-highlight-selected',
    preservedStopFeature ? createFeatureCollection([preservedStopFeature]) : emptyFeatureCollection
  )
}

function highlightStop(stopId) {
  selectedStopForRoutes = null
  setSelectedStopState(stopId)
  setStopsDimmed(false)
  const feature = findStopFeature(stopId)
  setSourceData('routes', emptyFeatureCollection)
  setSourceData('routes-path', emptyFeatureCollection)
  setSourceData('stops-highlight', emptyFeatureCollection)
  setSourceData('stops-highlight-selected', feature ? createFeatureCollection([feature]) : emptyFeatureCollection)
}

function highlightStopReachableRoutes(stop) {
  const resolvedStop = resolveStop(stop)
  if (!resolvedStop) return []

  selectedStopForRoutes = resolvedStop
  setSelectedStopState(resolvedStop.stop_id)
  setStopsDimmed(true)
  const feature = findStopFeature(resolvedStop.stop_id)
  const routes = reachableRouteFeatures(resolvedStop)

  setSourceData('routes', createFeatureCollection(routes))
  setSourceData('routes-path', emptyFeatureCollection)
  setSourceData('stops-highlight', emptyFeatureCollection)
  setSourceData('stops-highlight-selected', feature ? createFeatureCollection([feature]) : emptyFeatureCollection)

  return routes
}

function getFocusPadding() {
  const canvasRect = map.getCanvas().getBoundingClientRect()
  const leftPanel = document.querySelector('.map-info-dock, .map-mini-toggle')
  const rightPanel = document.querySelector('.map-chart-card')
  const leftRect = leftPanel ? leftPanel.getBoundingClientRect() : null
  const rightRect = rightPanel ? rightPanel.getBoundingClientRect() : null
  const isDesktop = canvasRect.width >= 900
  const sideGap = isDesktop ? 48 : 28
  const leftPadding = leftRect ? Math.max(36, leftRect.right - canvasRect.left + sideGap) : 36
  const rightPadding = rightRect ? Math.max(36, canvasRect.right - rightRect.left + sideGap) : 36

  return {
    top: 96,
    right: isDesktop ? rightPadding : 36,
    bottom: canvasRect.height >= 700 ? 120 : 72,
    left: isDesktop ? leftPadding : 36
  }
}

function buildBounds(coordinates) {
  if (!coordinates.length) return null

  return coordinates.reduce(
    (bounds, coordinate) => bounds.extend(coordinate),
    new maplibregl.LngLatBounds(coordinates[0], coordinates[0])
  )
}

function focusOnCoordinates(coordinates, maxZoom, duration) {
  if (!map || !coordinates.length) return

  if (coordinates.length === 1) {
    const lng = coordinates[0][0]
    const lat = coordinates[0][1]
    const delta = 0.0024
    const pointBounds = new maplibregl.LngLatBounds(
      [lng - delta, lat - delta],
      [lng + delta, lat + delta]
    )

    map.fitBounds(pointBounds, {
      padding: getFocusPadding(),
      maxZoom: maxZoom || 15,
      duration: duration === 0 ? 0 : 700,
      essential: true
    })
    return
  }

  const bounds = buildBounds(coordinates)
  if (!bounds) return

  map.fitBounds(bounds, {
    padding: getFocusPadding(),
    maxZoom: maxZoom || 14,
    duration: duration === 0 ? 0 : 700,
    essential: true
  })
}

function scheduleFocusOnCoordinates(coordinates, maxZoom) {
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      focusOnCoordinates(coordinates, maxZoom)
    })
  })
}

function fitStopBounds() {
  const coordinates = busStopsGeoJSON.features.map((feature) => feature.geometry.coordinates)
  focusOnCoordinates(coordinates, 13.4, 0)
}

function routeColorForLine(line) {
  const colorKey = Number(line.line_id) || String(line.service_no || line.line_code || line.line_name || '').split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
  return routePalette[Math.abs(colorKey) % routePalette.length]
}

function routeFeatureCoordinates(features) {
  return features.flatMap((feature) => feature.geometry?.coordinates || [])
}

function isValidCoordinate(coordinate) {
  return Array.isArray(coordinate)
    && coordinate.length >= 2
    && Number.isFinite(Number(coordinate[0]))
    && Number.isFinite(Number(coordinate[1]))
}

function normalizeCoordinates(coordinates) {
  return coordinates
    .filter(isValidCoordinate)
    .map((coordinate) => [Number(coordinate[0]), Number(coordinate[1])])
}

function interpolateCatmullRom(p0, p1, p2, p3, t) {
  const t2 = t * t
  const t3 = t2 * t

  return [
    0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
    0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
  ]
}

function smoothRouteCoordinates(coordinates) {
  const points = normalizeCoordinates(coordinates)
  if (points.length < 3) return points

  const smoothed = [points[0]]
  const segmentSteps = 8

  for (let index = 0; index < points.length - 1; index += 1) {
    const p0 = points[Math.max(0, index - 1)]
    const p1 = points[index]
    const p2 = points[index + 1]
    const p3 = points[Math.min(points.length - 1, index + 2)]

    for (let step = 1; step <= segmentSteps; step += 1) {
      smoothed.push(interpolateCatmullRom(p0, p1, p2, p3, step / segmentSteps))
    }
  }

  return smoothed
}

function addRouteSources() {
  if (map.getSource('routes')) return

  map.addSource('routes', {
    type: 'geojson',
    promoteId: 'line_id',
    data: busRoutesGeoJSON
  })

  map.addSource('routes-path', {
    type: 'geojson',
    promoteId: 'line_id',
    data: emptyFeatureCollection
  })
}

function addRouteLayers() {
  map.addLayer({
    id: 'routes-bg',
    type: 'line',
    source: 'routes',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': '#f7fbff',
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 4, 14, 6.2, 17, 8],
      'line-opacity': 1,
      'line-blur': ['interpolate', ['linear'], ['zoom'], 10, 0.08, 17, 0.18]
    }
  })

  map.addLayer({
    id: 'routes',
    type: 'line',
    source: 'routes',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': routeColorExpression,
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1.8, 14, 3, 17, 4.2],
      'line-opacity': 1,
      'line-blur': ['interpolate', ['linear'], ['zoom'], 10, 0, 17, 0.08]
    }
  })

  map.addLayer({
    id: 'routes-hit',
    type: 'line',
    source: 'routes',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': '#000000',
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 18, 14, 26, 17, 34],
      'line-opacity': 0.01
    }
  })

  map.addLayer({
    id: 'route-arrows',
    type: 'symbol',
    source: 'routes',
    minzoom: 12,
    layout: {
      'symbol-placement': 'line',
      'symbol-spacing': 180,
      'text-field': '>',
      'text-size': ['interpolate', ['linear'], ['zoom'], 12, 10, 16, 13],
      'text-keep-upright': false,
      'text-allow-overlap': true,
      'text-ignore-placement': true
    },
    paint: {
      'text-color': routeColorExpression,
      'text-halo-color': '#ffffff',
      'text-halo-width': 0.8,
      'text-opacity': 1
    }
  })

  map.addLayer({
    id: 'routes-path-bg',
    type: 'line',
    source: 'routes-path',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': '#f7fbff',
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 5.2, 14, 7.8, 17, 10.5],
      'line-opacity': 1,
      'line-blur': ['interpolate', ['linear'], ['zoom'], 10, 0.08, 17, 0.16]
    }
  })

  map.addLayer({
    id: 'routes-path',
    type: 'line',
    source: 'routes-path',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': routeColorExpression,
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 2.6, 14, 4.5, 17, 6.4],
      'line-opacity': 1,
      'line-blur': ['interpolate', ['linear'], ['zoom'], 10, 0, 17, 0.02]
    }
  })

  map.addLayer({
    id: 'route-path-arrows',
    type: 'symbol',
    source: 'routes-path',
    minzoom: 12,
    layout: {
      'symbol-placement': 'line',
      'symbol-spacing': 150,
      'text-field': '>',
      'text-size': ['interpolate', ['linear'], ['zoom'], 12, 11, 16, 14],
      'text-keep-upright': false,
      'text-allow-overlap': true,
      'text-ignore-placement': true
    },
    paint: {
      'text-color': routeColorExpression,
      'text-halo-color': '#ffffff',
      'text-halo-width': 1,
      'text-opacity': 1
    }
  })
}

function addStopSources() {
  if (map.getSource('stops')) return

  map.addSource('stops', {
    type: 'geojson',
    tolerance: 10,
    buffer: 0,
    promoteId: 'stop_id',
    data: busStopsGeoJSON
  })

  map.addSource('stops-highlight', {
    type: 'geojson',
    promoteId: 'stop_id',
    data: emptyFeatureCollection
  })

  map.addSource('stops-highlight-selected', {
    type: 'geojson',
    promoteId: 'stop_id',
    data: emptyFeatureCollection
  })
}

function addStopLayers() {
  map.addLayer({
    id: 'stops-hit',
    type: 'circle',
    source: 'stops',
    minzoom: 12,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 12, 14, 17, 17, 23],
      'circle-color': '#000000',
      'circle-opacity': 0.01
    }
  })

  map.addLayer({
    id: 'stops-hub',
    type: 'circle',
    source: 'stops',
    minzoom: 9,
    maxzoom: 12,
    filter: ['>=', ['to-number', ['get', 'service_count']], 3],
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 2, 10.5, 2.8, 12, 3.4],
      'circle-color': stopPriorityColorExpression,
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 9, 0.4, 11, 0.7],
      'circle-opacity': 0.82
    }
  })
  map.addLayer({
    id: 'stops',
    type: 'circle',
    source: 'stops',
    minzoom: 9,
    maxzoom: 15,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 0.6, 11, 1, 13, 2, 14, 3.5, 15, ['case', ['boolean', ['feature-state', 'selected'], false], 7, 5]],
      'circle-color': ['case', ['boolean', ['feature-state', 'selected'], false], '#ffffff', stopPriorityColorExpression],
      'circle-stroke-color': ['case', ['boolean', ['feature-state', 'selected'], false], stopStroke, '#ffffff'],
      'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 9, 0, 12, 0.5, 15, 1.5],
      'circle-stroke-opacity': ['interpolate', ['linear'], ['zoom'], 9, 0, 12, 0.35, 15, 0.85],
      'circle-opacity': stopsOpacityByZoom
    }
  })

  map.addLayer({
    id: 'stops-detail',
    type: 'circle',
    source: 'stops',
    minzoom: 13.5,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 14, 2, 15, ['case', ['boolean', ['feature-state', 'selected'], false], 9, 5], 17, ['case', ['boolean', ['feature-state', 'selected'], false], 12, 7]],
      'circle-color': ['case', ['boolean', ['feature-state', 'selected'], false], '#ffffff', stopPriorityColorExpression],
      'circle-stroke-color': ['case', ['boolean', ['feature-state', 'selected'], false], stopStroke, '#ffffff'],
      'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 14, 1, 15, 2, 17, 3],
      'circle-stroke-opacity': ['interpolate', ['linear'], ['zoom'], 14, 0, 14.5, 0.62, 17, 0.9],
      'circle-opacity': 1
    }
  })
  map.addLayer({
    id: 'stop-labels',
    type: 'symbol',
    source: 'stops',
    minzoom: 15,
    layout: {
      'text-field': ['step', ['zoom'], ['get', 'station_code'], 16, ['format', ['get', 'station_code'], { 'font-scale': 0.8 }, '\n', {}, ['get', 'stop_name'], { 'font-scale': 1 }]],
      'text-size': ['interpolate', ['linear'], ['zoom'], 15, 14, 17, 17],
      'text-anchor': 'left',
      'text-offset': [0.8, 0],
      'text-max-width': 14,
      'text-optional': true,
      'text-padding': 2,
      'text-allow-overlap': false,
      'text-ignore-placement': false
    },
    paint: {
      'text-color': '#1f2937',
      'text-halo-color': '#ffffff',
      'text-halo-width': 1.5,
      'text-halo-blur': 0.5,
      'text-opacity': stopLabelsOpacityByZoom
    }
  })
  map.addLayer({
    id: 'stops-highlight',
    type: 'circle',
    source: 'stops-highlight',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 10.5, 0.9, 11.5, 1.4, 13, 2, 15, 3.1, 17, 4.4],
      'circle-color': stopPriorityColorExpression,
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 10.5, 0, 14, 0.4, 17, 0.75],
      'circle-stroke-opacity': ['interpolate', ['linear'], ['zoom'], 10.5, 0, 14, 0.34, 17, 0.62],
      'circle-opacity': ['interpolate', ['linear'], ['zoom'], 10.5, 0.82, 14, 0.9, 17, 0.90]
    }
  })

  map.addLayer({
    id: 'stops-highlight-selected',
    type: 'circle',
    source: 'stops-highlight-selected',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 10.5, 4.5, 12, 6, 14, 8, 17, 11],
      'circle-color': 'rgba(255,255,255,0)',
      'circle-stroke-color': stopStroke,
      'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 10.5, 1.2, 12, 1.8, 14, 2.5, 17, 3.4],
      'circle-opacity': 1
    }
  })
}

function registerPmtilesProtocol() {
  try {
    maplibregl.removeProtocol && maplibregl.removeProtocol('pmtiles')
  } catch {
    // MapLibre throws if the protocol was not registered yet.
  }

  pmtilesProtocol = new Protocol()
  maplibregl.addProtocol('pmtiles', pmtilesProtocol.tile)
}

function bindStopLayerEvents() {
  map.on('mouseenter', 'stops-hit', () => {
    map.getCanvas().style.cursor = 'pointer'
  })

  map.on('mouseleave', 'stops-hit', () => {
    map.getCanvas().style.cursor = ''
  })

  map.on('click', 'stops-hit', (event) => {
    event.preventDefault()
    const feature = event.features && event.features[0]
    const stopId = feature && feature.properties ? feature.properties.stop_id : ''
    const stop = busStops.find((item) => String(item.stop_id) === String(stopId))

    if (!stop) return

    emit('select-stop', stop)
    scheduleFocusOnCoordinates([[stop.lng, stop.lat]], 17)
  })
}

function bindRouteLayerEvents() {
  map.on('mouseenter', 'routes-hit', () => {
    map.getCanvas().style.cursor = 'pointer'
  })

  map.on('mouseleave', 'routes-hit', () => {
    map.getCanvas().style.cursor = ''
  })

  map.on('click', 'routes-hit', (event) => {
    if (event.defaultPrevented) return

    const renderedFeature = event.features && event.features[0]
    if (!renderedFeature) return

    const routeId = renderedFeature.properties ? renderedFeature.properties.line_id : ''
    const feature = findRouteFeature(routeId)
    if (!feature) return

    const routeCoordinates = feature.geometry.coordinates
    highlightRoute(feature)
    emit('select-route', {
      ...feature.properties,
      coordinates: routeCoordinates
    })

    scheduleFocusOnCoordinates(routeCoordinates, 14)
  })
}

function focusRouteById(routeId, options = {}) {
  const feature = findRouteFeature(routeId)
  if (!feature || !map || !map.getSource('routes-path')) return null

  highlightRoute(feature, options)
  scheduleFocusOnCoordinates(feature.geometry.coordinates, 14)

  return {
    ...feature.properties,
    coordinates: feature.geometry.coordinates
  }
}

function focusStopByName(name) {
  const text = (name || '').trim()
  if (!text || !map || !map.getSource('stops-highlight-selected')) return null

  const normalizedText = text.toLowerCase()
  const stop = busStops.find((item) =>
    item.stop_name.toLowerCase() === normalizedText || item.station_code === text
  )

  if (!stop) return null

  highlightStop(stop.stop_id)
  scheduleFocusOnCoordinates([[stop.lng, stop.lat]], 15.6)

  return stop
}

function stationToFeature(station) {
  const stationCode = String(station.station_code || station.bus_stop_code || '').padStart(5, '0')
  const isPriorityStop = PRIORITY_BUS_STOP_CODES.has(stationCode)

  return {
    type: 'Feature',
    id: String(station.station_id),
    geometry: {
      type: 'Point',
      coordinates: [Number(station.longitude), Number(station.latitude)]
    },
    properties: {
      stop_id: String(station.station_id),
      stop_name: station.station_name,
      station_code: stationCode,
      road_name: station.road_name || station.address || '',
      is_priority_stop: isPriorityStop,
      line_ids: JSON.stringify(station.line_ids || []),
      service_nos: Array.isArray(station.service_nos) ? station.service_nos.join('|') : station.service_nos || '',
      service_count: Array.isArray(station.service_nos) ? station.service_nos.length : Number(station.service_count) || 0
    }
  }
}

function stationToStop(station) {
  return {
    stop_id: String(station.station_id),
    stop_name: station.station_name,
    station_code: station.station_code || station.bus_stop_code || '',
    bus_stop_code: station.bus_stop_code || station.station_code || '',
    road_name: station.road_name || station.address || '',
    line_ids: station.line_ids || [],
    line_names: station.line_names || [],
    service_nos: station.service_nos || [],
    lng: Number(station.longitude),
    lat: Number(station.latitude),
    passing_routes: [station.service_nos, station.line_names, station.line_ids].flat().filter(Boolean),
    crowd_level: null,
    eta_minutes: null
  }
}

async function getCachedMapStations() {
  if (mapDataCache.stops) return mapDataCache.stops
  if (!mapDataCache.stopsPromise) {
    mapDataCache.stopsPromise = runWithRetry(() => getMapStations())
      .then((response) => {
        const stations = response?.data?.stations || response?.data?.items || []
        const validStations = stations.filter((station) => Number.isFinite(Number(station.longitude)) && Number.isFinite(Number(station.latitude)))
        if (!validStations.length) return null
        const data = {
          stops: validStations.map(stationToStop),
          geojson: createFeatureCollection(validStations.map(stationToFeature))
        }
        mapDataCache.stops = data
        return data
      })
      .finally(() => {
        mapDataCache.stopsPromise = null
      })
  }
  return mapDataCache.stopsPromise
}
async function loadRealBusStops() {
  try {
    const stopData = await getCachedMapStations()
    if (!stopData) return
    busStops = stopData.stops
    busStopsGeoJSON = stopData.geojson
    setSourceData('stops', busStopsGeoJSON)
    if (!isStopBoundsFitted) {
      fitStopBounds()
      isStopBoundsFitted = true
    }
  } catch (error) {
    console.warn('map stations load failed', error?.message)
    emit('load-error', '地图站点加载失败，请检查后端和数据库。')
  }
}
function lineToFeature(line) {
  const coordinates = smoothRouteCoordinates(Array.isArray(line.path_coordinates) ? line.path_coordinates : [])
  return {
    type: 'Feature',
    id: Number(line.line_id),
    properties: {
      line_id: Number(line.line_id),
      line_name: line.line_name,
      line_code: line.line_code,
      service_no: line.service_no,
      direction: line.direction,
      start_station: line.start_station,
      end_station: line.end_station,
      color: line.color,
      crowd_level: line.crowd_level,
      load_code: line.load_code,
      load_score: line.load_score,
      display_color: routeColorForLine(line)
    },
    geometry: {
      type: 'LineString',
      coordinates
    }
  }
}

function mergeSegmentCoordinates(segments) {
  return [...segments]
    .sort((a, b) => Number(a.stop_sequence || 0) - Number(b.stop_sequence || 0))
    .reduce((coordinates, segment) => {
      const path = Array.isArray(segment.path_coordinates) ? segment.path_coordinates : []
      path.forEach((coordinate) => {
        const previous = coordinates[coordinates.length - 1]
        if (!previous || previous[0] !== coordinate[0] || previous[1] !== coordinate[1]) coordinates.push(coordinate)
      })
      return coordinates
    }, [])
}

async function loadRouteGeometryFallback(lines) {
  try {
    const lineIds = lines.map((line) => line.line_id).filter(Boolean).join(',')
    const segmentResponse = await runWithRetry(() => getRoadSegments(lineIds ? { line_ids: lineIds } : undefined), 2)
    const segments = segmentResponse?.data?.segments || []
    const segmentsByLine = new Map()

    segments.forEach((segment) => {
      const key = Number(segment.line_id)
      if (!segmentsByLine.has(key)) segmentsByLine.set(key, [])
      segmentsByLine.get(key).push(segment)
    })

    const data = createFeatureCollection(
      lines
        .map((line) => {
          if (Array.isArray(line.path_coordinates) && line.path_coordinates.length >= 2) return line
          return { ...line, path_coordinates: mergeSegmentCoordinates(segmentsByLine.get(Number(line.line_id)) || []) }
        })
        .filter((line) => Array.isArray(line.path_coordinates) && line.path_coordinates.length >= 2)
        .map(lineToFeature)
    )

    if (!data.features.length) return null

    mapDataCache.routes = data
    busRoutesGeoJSON = data
    if (selectedStopForRoutes && areRoutesVisible) {
      highlightStopReachableRoutes(selectedStopForRoutes)
    } else if (areRoutesVisible) {
      setSourceData('routes', busRoutesGeoJSON)
    }
    return data
  } catch (error) {
    console.warn('map road segments fallback failed', error?.message)
    return null
  }
}

async function getCachedMapRoutes() {
  if (mapDataCache.routes) return mapDataCache.routes
  if (!mapDataCache.routesPromise) {
    mapDataCache.routesPromise = runWithRetry(() => getMapLines())
      .then((lineResponse) => {
        const lines = lineResponse?.data?.lines || []
        const selectedLines = visibleLineIds.size
          ? lines.filter((line) => visibleLineIds.has(Number(line.line_id)))
          : lines
        const completeLines = selectedLines.filter(
          (line) => Array.isArray(line.path_coordinates) && line.path_coordinates.length >= 2
        )
        const data = createFeatureCollection(completeLines.map(lineToFeature))
        const hasIncompleteLines = completeLines.length < selectedLines.length

        if (data.features.length) {
          mapDataCache.routes = data
          if (hasIncompleteLines) void loadRouteGeometryFallback(selectedLines)
          return data
        }

        if (hasIncompleteLines) return loadRouteGeometryFallback(selectedLines)
        return null
      })
      .finally(() => {
        mapDataCache.routesPromise = null
      })
  }
  return mapDataCache.routesPromise
}
async function loadRealBusRoutes() {
  if (busRoutesLoaded) return
  if (routesLoadPromise) return routesLoadPromise

  routesLoadPromise = (async () => {
    try {
      const data = await getCachedMapRoutes()
      if (!data) return
      busRoutesGeoJSON = data
      busRoutesLoaded = true
      // 初始不显示路线，等待后续调用 showStationRoutes 或 showAllRoutes 再显示
      // if (selectedStopForRoutes) {
      //   highlightStopReachableRoutes(selectedStopForRoutes)
      // } else if (map && map.getSource('routes')) {
      //   setSourceData('routes', busRoutesGeoJSON)
      // }
    } catch (error) {
      console.warn('map routes load failed', error?.message)
      emit('load-error', '地图线路加载失败，请检查后端和数据库。')
    } finally {
      routesLoadPromise = null
    }
  })()

  return routesLoadPromise
}
onMounted(() => {
  registerPmtilesProtocol()

  map = new maplibregl.Map({
    container: mapContainer.value,
    style: createProtomapsStyle(),
    center: [103.8198, 1.3521],
    zoom: 11
  })

  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

  const initialDataPromise = Promise.allSettled([
    loadRealBusStops(),
    loadRealBusRoutes()
  ])

  initialDataPromise.then(() => {
    if (map) emit('initial-data-loaded')
  })

  map.on('load', () => {
    addRouteSources()
    addStopSources()
    addRouteLayers()
    addStopLayers()
    bindRouteLayerEvents()
    bindStopLayerEvents()

    if (busStopsGeoJSON.features.length) setSourceData('stops', busStopsGeoJSON)
    if (!isStopBoundsFitted && busStopsGeoJSON.features.length) {
      fitStopBounds()
      isStopBoundsFitted = true
    }
    if (busRoutesGeoJSON.features.length && map.getSource('routes') && areRoutesVisible) {
      if (selectedStopForRoutes) {
        highlightStopReachableRoutes(selectedStopForRoutes)
      } else {
        setSourceData('routes', busRoutesGeoJSON)
      }
    }
  })
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }

  if (pmtilesProtocol && maplibregl.removeProtocol) {
    try {
      maplibregl.removeProtocol('pmtiles')
    } catch {
      // Ignore cleanup errors during hot reload or repeated unmounts.
    }
    pmtilesProtocol = null
  }
})

async function reloadMapData() {
  mapDataCache.stops = null
  mapDataCache.routes = null
  mapDataCache.stopsPromise = null
  mapDataCache.routesPromise = null
  routesLoadPromise = null
  busRoutesLoaded = false
  isStopBoundsFitted = false
  areRoutesVisible = false
  await Promise.allSettled([
    loadRealBusStops(),
    loadRealBusRoutes()
  ])
}

function showStationRoutes(stop) {
  if (!map || !map.getSource('routes')) return
  const resolvedStop = resolveStop(stop)
  if (!resolvedStop) return
  selectedStopForRoutes = resolvedStop
  areRoutesVisible = true
  highlightStopReachableRoutes(resolvedStop)
  const feature = findStopFeature(resolvedStop.stop_id)
  if (feature) {
    scheduleFocusOnCoordinates([feature.geometry.coordinates], 15)
  }
}

function showAllRoutes() {
  if (!map || !map.getSource('routes')) return
  selectedStopForRoutes = null
  areRoutesVisible = true
  setStopsDimmed(false)
  setSelectedStopState(null)
  setSourceData('routes', busRoutesGeoJSON)
  setSourceData('routes-path', emptyFeatureCollection)
  setSourceData('stops-highlight', emptyFeatureCollection)
  setSourceData('stops-highlight-selected', emptyFeatureCollection)
}

function hideRoutes() {
  if (!map || !map.getSource('routes')) return
  selectedStopForRoutes = null
  areRoutesVisible = false
  setSourceData('routes', emptyFeatureCollection)
  setSourceData('routes-path', emptyFeatureCollection)
  setSourceData('stops-highlight', emptyFeatureCollection)
  setSourceData('stops-highlight-selected', emptyFeatureCollection)
}

defineExpose({
  clearSelection,
  focusRouteById,
  focusStopByName,
  reloadMapData,
  showStationRoutes,
  showAllRoutes,
  hideRoutes,
  getStopRoutes
})
</script>

<style scoped>
.bus-map-wrapper {
  width: 100%;
  height: 100%;
  min-height: 600px;
}

.bus-map {
  width: 100%;
  height: 100%;
}
</style>
