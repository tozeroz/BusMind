<template>
  <div class="bus-map-wrapper">
    <div ref="mapContainer" class="bus-map"></div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import maplibregl from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import 'maplibre-gl/dist/maplibre-gl.css'

import { createProtomapsStyle } from '@/map/map-style'
import {
  mockBusRouteGeoJSON,
  mockBusStops,
  mockBusStopsGeoJSON
} from '@/map/mock-bus-data'

const emit = defineEmits(['select-stop', 'select-route'])

const mapContainer = ref(null)
let map = null
let pmtilesProtocol = null
let selectedStopId = ''
let selectedRouteId = ''

const loadColorExpression = [
  'match',
  ['get', 'crowd_level'],
  'low',
  '#25c46a',
  'medium',
  '#f4a62a',
  'high',
  '#ef4444',
  '#4f8fca'
]
const selectedColor = '#f8f4d8'
const selectedStrokeColor = '#24364d'

function routeColorExpression() {
  return [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    selectedColor,
    loadColorExpression
  ]
}

function routeWidthExpression() {
  return [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    ['interpolate', ['linear'], ['zoom'], 10, 8, 14, 12, 17, 16],
    ['interpolate', ['linear'], ['zoom'], 10, 4, 14, 7, 17, 10]
  ]
}

function stopColorExpression() {
  return [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    selectedColor,
    loadColorExpression
  ]
}

function stopRadiusExpression() {
  return [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    ['interpolate', ['linear'], ['zoom'], 10, 9, 14, 14, 17, 18],
    ['interpolate', ['linear'], ['zoom'], 10, 6, 14, 9, 17, 13]
  ]
}

function stopStrokeColorExpression() {
  return [
    'case',
    ['boolean', ['feature-state', 'selected'], false],
    selectedStrokeColor,
    '#ffffff'
  ]
}

function setFeatureSelected(source, id, selected) {
  if (!map || !id) return
  map.setFeatureState({ source, id }, { selected })
}

function clearSelection() {
  setFeatureSelected('bus-stops-source', selectedStopId, false)
  setFeatureSelected('bus-route-source', selectedRouteId, false)
  selectedStopId = ''
  selectedRouteId = ''
}

function selectStopFeature(stopId) {
  clearSelection()
  selectedStopId = stopId
  setFeatureSelected('bus-stops-source', selectedStopId, true)
}

function selectRouteFeature(routeId) {
  clearSelection()
  selectedRouteId = routeId
  setFeatureSelected('bus-route-source', selectedRouteId, true)
}

function updateInitialPaint() {
  if (!map) return

  if (map.getLayer('bus-route-line')) {
    map.setPaintProperty('bus-route-line', 'line-color', routeColorExpression())
    map.setPaintProperty('bus-route-line', 'line-width', routeWidthExpression())
  }

  if (map.getLayer('bus-stops-circle')) {
    map.setPaintProperty('bus-stops-circle', 'circle-color', stopColorExpression())
    map.setPaintProperty('bus-stops-circle', 'circle-radius', stopRadiusExpression())
    map.setPaintProperty('bus-stops-circle', 'circle-stroke-color', stopStrokeColorExpression())
  }
}

function focusOnCoordinate(coordinates, zoom = 14.5) {
  const canvas = map.getCanvas()
  map.easeTo({
    center: coordinates,
    zoom: Math.max(map.getZoom(), zoom),
    offset: [-canvas.clientWidth * 0.18, canvas.clientHeight * 0.18],
    duration: 700,
    essential: true
  })
}

function getLineMidpoint(coordinates) {
  return coordinates[Math.floor(coordinates.length / 2)] || coordinates[0]
}

function fitRouteBounds() {
  const coordinates = mockBusRouteGeoJSON.features.flatMap((feature) => feature.geometry.coordinates)
  if (!coordinates.length) return

  const bounds = coordinates.reduce(
    (result, coordinate) => result.extend(coordinate),
    new maplibregl.LngLatBounds(coordinates[0], coordinates[0])
  )

  map.fitBounds(bounds, {
    padding: { top: 90, right: 220, bottom: 90, left: 420 },
    maxZoom: 13.6,
    duration: 0
  })
}

function addBusRouteLayer() {
  if (map.getSource('bus-route-source')) return

  map.addSource('bus-route-source', {
    type: 'geojson',
    data: mockBusRouteGeoJSON
  })

  map.addLayer({
    id: 'bus-route-line',
    type: 'line',
    source: 'bus-route-source',
    layout: {
      'line-cap': 'round',
      'line-join': 'round'
    },
    paint: {
      'line-color': routeColorExpression(),
      'line-width': routeWidthExpression(),
      'line-opacity': 0.85
    }
  })

  map.addLayer({
    id: 'bus-route-hit',
    type: 'line',
    source: 'bus-route-source',
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
}

function addBusStopLayers() {
  if (map.getSource('bus-stops-source')) return

  map.addSource('bus-stops-source', {
    type: 'geojson',
    data: mockBusStopsGeoJSON
  })

  map.addLayer({
    id: 'bus-stops-circle',
    type: 'circle',
    source: 'bus-stops-source',
    paint: {
      'circle-radius': stopRadiusExpression(),
      'circle-color': stopColorExpression(),
      'circle-stroke-color': stopStrokeColorExpression(),
      'circle-stroke-width': 2,
      'circle-opacity': 0.95
    }
  })

  map.addLayer({
    id: 'bus-stops-label',
    type: 'symbol',
    source: 'bus-stops-source',
    minzoom: 12,
    layout: {
      'text-field': ['get', 'stop_name'],
      'text-font': ['Open Sans Regular', 'Arial Unicode MS Regular'],
      'text-size': ['interpolate', ['linear'], ['zoom'], 12, 11, 16, 13],
      'text-offset': [0, 1.25],
      'text-anchor': 'top',
      'text-allow-overlap': false,
      'text-optional': true
    },
    paint: {
      'text-color': '#16324f',
      'text-halo-color': '#ffffff',
      'text-halo-width': 1.4
    }
  })
}

function registerPmtilesProtocol() {
  try {
    maplibregl.removeProtocol?.('pmtiles')
  } catch {
    // MapLibre throws if the protocol was not registered yet.
  }

  pmtilesProtocol = new Protocol()
  maplibregl.addProtocol('pmtiles', pmtilesProtocol.tile)
}

function bindStopLayerEvents() {
  map.on('mouseenter', 'bus-stops-circle', () => {
    map.getCanvas().style.cursor = 'pointer'
  })

  map.on('mouseleave', 'bus-stops-circle', () => {
    map.getCanvas().style.cursor = ''
  })

  map.on('click', 'bus-stops-circle', (event) => {
    const feature = event.features?.[0]
    const stopId = feature?.properties?.stop_id
    const stop = mockBusStops.find((item) => item.stop_id === stopId)

    if (!stop) return

    selectStopFeature(stop.stop_id)
    emit('select-stop', stop)
    focusOnCoordinate([stop.lng, stop.lat], 14.5)
  })
}

function bindRouteLayerEvents() {
  map.on('mouseenter', 'bus-route-hit', () => {
    map.getCanvas().style.cursor = 'pointer'
  })

  map.on('mouseleave', 'bus-route-hit', () => {
    map.getCanvas().style.cursor = ''
  })

  map.on('click', 'bus-route-hit', (event) => {
    const stopsAtPoint = map.queryRenderedFeatures(event.point, {
      layers: ['bus-stops-circle']
    })
    if (stopsAtPoint.length) return

    const feature = event.features?.[0]
    if (!feature) return

    selectRouteFeature(feature.id || feature.properties?.line_id)
    emit('select-route', {
      ...feature.properties,
      coordinates: feature.geometry?.coordinates || []
    })

    const midpoint = getLineMidpoint(feature.geometry?.coordinates || [])
    if (midpoint) focusOnCoordinate(midpoint, 13.8)
  })
}

onMounted(() => {
  registerPmtilesProtocol()

  const mapStyle = createProtomapsStyle()

  map = new maplibregl.Map({
    container: mapContainer.value,
    style: mapStyle,
    center: [103.8198, 1.3521],
    zoom: 11
  })

  map.addControl(new maplibregl.NavigationControl(), 'top-right')

  map.on('load', () => {
    addBusRouteLayer()
    addBusStopLayers()
    updateInitialPaint()
    fitRouteBounds()
    bindRouteLayerEvents()
    bindStopLayerEvents()
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


