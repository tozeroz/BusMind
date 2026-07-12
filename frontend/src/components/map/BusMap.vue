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

import { getMapLines, getMapStations } from '@/api/map'
import { getLines } from '@/api/transit'
import { createProtomapsStyle } from '@/map/map-style'

const emit = defineEmits(['select-stop', 'select-route'])

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
let isRouteBoundsFitted = false

const emptyFeatureCollection = {
  type: 'FeatureCollection',
  features: []
}

const routeRed = '#e11d2e'
const routeMuted = '#2563eb'
const routeBg = '#ffffff'
const stopFill = '#ffffff'
const stopStroke = '#e11d2e'
const stopMutedStroke = '#2563eb'

function getSource(sourceId) {
  return map && map.getSource(sourceId)
}

function setSourceData(sourceId, data) {
  const source = getSource(sourceId)
  if (source) source.setData(data)
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

function findRouteFeature(routeId) {
  const id = Number(routeId)
  return busRoutesGeoJSON.features.find((feature) => {
    return Number(feature.id) === id || Number(feature.properties.line_id) === id
  })
}

function findStopFeature(stopId) {
  return busStopsGeoJSON.features.find((feature) => String(feature.properties.stop_id) === String(stopId))
}

function clearSelection() {
  setSourceData('routes-path', emptyFeatureCollection)
  setSourceData('stops-highlight', emptyFeatureCollection)
  setSourceData('stops-highlight-selected', emptyFeatureCollection)
}

function highlightRoute(feature) {
  const routeCoordinates = feature.geometry.coordinates
  setSourceData('routes-path', createFeatureCollection([feature]))
  setSourceData('stops-highlight', createFeatureCollection(routeStopFeatures(routeCoordinates)))
  setSourceData('stops-highlight-selected', emptyFeatureCollection)
}

function highlightStop(stopId) {
  const feature = findStopFeature(stopId)
  setSourceData('routes-path', emptyFeatureCollection)
  setSourceData('stops-highlight', emptyFeatureCollection)
  setSourceData('stops-highlight-selected', feature ? createFeatureCollection([feature]) : emptyFeatureCollection)
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

function fitRouteBounds() {
  const coordinates = busRoutesGeoJSON.features.flatMap((feature) => feature.geometry.coordinates)
  focusOnCoordinates(coordinates, 13.4, 0)
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
      'line-color': routeBg,
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 7, 14, 10, 17, 13],
      'line-opacity': 0.72
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
      'line-color': routeMuted,
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 4, 14, 6, 17, 8],
      'line-opacity': 0.74
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
      'symbol-spacing': 120,
      'text-field': '>',
      'text-size': ['interpolate', ['linear'], ['zoom'], 12, 12, 16, 16],
      'text-keep-upright': false,
      'text-allow-overlap': true,
      'text-ignore-placement': true
    },
    paint: {
      'text-color': routeMuted,
      'text-halo-color': '#ffffff',
      'text-halo-width': 0.8,
      'text-opacity': 0.55
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
      'line-color': routeBg,
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 11, 14, 15, 17, 20],
      'line-opacity': 1
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
      'line-color': routeRed,
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 7, 14, 10, 17, 14],
      'line-opacity': 1
    }
  })

  map.addLayer({
    id: 'route-path-arrows',
    type: 'symbol',
    source: 'routes-path',
    minzoom: 12,
    layout: {
      'symbol-placement': 'line',
      'symbol-spacing': 90,
      'text-field': '>',
      'text-size': ['interpolate', ['linear'], ['zoom'], 12, 14, 16, 18],
      'text-keep-upright': false,
      'text-allow-overlap': true,
      'text-ignore-placement': true
    },
    paint: {
      'text-color': routeRed,
      'text-halo-color': '#ffffff',
      'text-halo-width': 1.2
    }
  })
}

function addStopSources() {
  if (map.getSource('stops')) return

  map.addSource('stops', {
    type: 'geojson',
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
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 15, 14, 21, 17, 28],
      'circle-color': '#000000',
      'circle-opacity': 0.01
    }
  })

  map.addLayer({
    id: 'stops',
    type: 'circle',
    source: 'stops',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 7, 14, 10, 17, 13],
      'circle-color': stopFill,
      'circle-stroke-color': stopMutedStroke,
      'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 10, 2.5, 14, 3.5, 17, 4],
      'circle-opacity': 0.98
    }
  })

  map.addLayer({
    id: 'stops-highlight',
    type: 'circle',
    source: 'stops-highlight',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 9, 14, 13, 17, 17],
      'circle-color': stopFill,
      'circle-stroke-color': stopStroke,
      'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 10, 4, 14, 5, 17, 6],
      'circle-opacity': 1
    }
  })

  map.addLayer({
    id: 'stops-highlight-selected',
    type: 'circle',
    source: 'stops-highlight-selected',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 14, 14, 20, 17, 26],
      'circle-color': 'rgba(255,255,255,0)',
      'circle-stroke-color': stopStroke,
      'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 10, 4, 14, 6, 17, 8],
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

    highlightStop(stop.stop_id)
    emit('select-stop', stop)
    scheduleFocusOnCoordinates([[stop.lng, stop.lat]], 15)
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

function focusRouteById(routeId) {
  const feature = findRouteFeature(routeId)
  if (!feature || !map || !map.getSource('routes-path')) return null

  highlightRoute(feature)
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
      station_code: station.station_code || station.bus_stop_code || '',
      road_name: station.road_name || station.address || ''
    }
  }
}

async function loadRealBusStops() {
  try {
    const linesResponse = await getLines({ page: 1, limit: 10 })
    const visibleLines = (linesResponse?.data?.lines || [])
      .filter((line) => !String(line.line_code || '').includes('{{'))
      .filter((line) => !String(line.line_name || '').toLowerCase().includes('postman test'))
      .slice(0, 9)

    visibleLineIds = new Set(visibleLines.map((line) => Number(line.line_id)))

    const stationResponses = await Promise.all(
      visibleLines.map((line) => getMapStations({ line_id: line.line_id }))
    )
    const stationById = new Map()
    stationResponses.forEach((response) => {
      ;(response?.data?.stations || []).forEach((station) => {
        const existing = stationById.get(station.station_id)
        if (!existing) {
          stationById.set(station.station_id, station)
          return
        }
        existing.service_nos = [...new Set([...(existing.service_nos || []), ...(station.service_nos || [])])]
      })
    })
    const stations = [...stationById.values()]
    busStops = stations
      .filter((station) => Number.isFinite(Number(station.longitude)) && Number.isFinite(Number(station.latitude)))
      .map((station) => ({
        stop_id: String(station.station_id),
        stop_name: station.station_name,
        station_code: station.station_code || station.bus_stop_code || '',
        road_name: station.road_name || station.address || '',
        lng: Number(station.longitude),
        lat: Number(station.latitude),
        passing_routes: station.service_nos || [],
        crowd_level: null,
        predicted_eta_minutes: null
      }))
    busStopsGeoJSON = createFeatureCollection(stations.map(stationToFeature))
    setSourceData('stops', busStopsGeoJSON)

    await loadRealBusRoutes()
  } catch (error) {
    console.warn('真实地图站点加载失败。', error?.message)
  }
}

function lineToFeature(line) {
  const coordinates = Array.isArray(line.path_coordinates) ? line.path_coordinates : []
  return {
    type: 'Feature',
    id: Number(line.line_id),
    properties: {
      line_id: Number(line.line_id),
      line_name: line.line_name,
      line_code: line.line_code,
      service_no: line.service_no,
      start_station: line.start_station,
      end_station: line.end_station,
      color: line.color
    },
    geometry: {
      type: 'LineString',
      coordinates
    }
  }
}

async function loadRealBusRoutes() {
  if (busRoutesLoaded) return
  if (!visibleLineIds.size) return

  try {
    const response = await getMapLines()
    const lines = response?.data?.lines || []
    const selectedLines = lines.filter((line) => visibleLineIds.has(Number(line.line_id)))

    busRoutesGeoJSON = createFeatureCollection(
      selectedLines
        .filter((line) => Array.isArray(line.path_coordinates) && line.path_coordinates.length >= 2)
        .map(lineToFeature)
    )

    busRoutesLoaded = true

    if (map && map.getSource('routes')) {
      setSourceData('routes', busRoutesGeoJSON)
      if (!isRouteBoundsFitted) {
        fitRouteBounds()
        isRouteBoundsFitted = true
      }
    }
  } catch (error) {
    console.warn('真实地图线路加载失败。', error?.message)
  }
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

  map.on('load', () => {
    addRouteSources()
    addStopSources()
    addRouteLayers()
    addStopLayers()
    bindRouteLayerEvents()
    bindStopLayerEvents()
    loadRealBusStops()
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

defineExpose({
  clearSelection,
  focusRouteById,
  focusStopByName
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