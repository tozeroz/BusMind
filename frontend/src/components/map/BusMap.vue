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

const emit = defineEmits(['select-stop'])

const mapContainer = ref(null)
let map = null
let pmtilesProtocol = null

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
      'line-color': [
        'match',
        ['get', 'crowd_level'],
        'low',
        '#2ecc71',
        'medium',
        '#f39c12',
        'high',
        '#e74c3c',
        '#409eff'
      ],
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 4, 14, 7, 17, 10],
      'line-opacity': 0.85
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
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10,
        6,
        14,
        9,
        17,
        13
      ],
      'circle-color': [
        'match',
        ['get', 'crowd_level'],
        'low',
        '#2ecc71',
        'medium',
        '#f39c12',
        'high',
        '#e74c3c',
        '#409eff'
      ],
      'circle-stroke-color': '#ffffff',
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

    emit('select-stop', stop)
    map.flyTo({
      center: [stop.lng, stop.lat],
      zoom: Math.max(map.getZoom(), 14.5),
      essential: true
    })
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


