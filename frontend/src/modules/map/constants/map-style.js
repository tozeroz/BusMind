/**
 * 文件：src/modules/map/constants/map-style.js
 * 用途：定义地图业务模块使用的固定配置。
 * 存放内容：底图样式、颜色、图层配置或其他不可变地图参数。
 * 实现功能：为地图组件提供统一配置，避免在组件内重复声明固定数据。
 */
import { layers, namedFlavor } from '@protomaps/basemaps'

const TILES_ROOT = '/tiles/'
const singaporeTilesUrl = `${TILES_ROOT}singapore.pmtiles`
const singaporeBuildingsTilesUrl = `${TILES_ROOT}singapore-buildings.pmtiles`

const PROTOMAPS_GLYPHS_URL =
  'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf'
const PROTOMAPS_SPRITE_URL =
  'https://protomaps.github.io/basemaps-assets/sprites/v4/light'

export const oneMapGreyLiteStyle = {
  version: 8,
  sources: {
    oneMap: {
      type: 'raster',
      tiles: [
        'https://www.onemap.gov.sg/maps/tiles/GreyLite/{z}/{x}/{y}.png'
      ],
      tileSize: 256,
      attribution: 'OneMap | Singapore Land Authority'
    }
  },
  layers: [
    {
      id: 'one-map-base-layer',
      type: 'raster',
      source: 'oneMap'
    }
  ]
}

export const osmRasterStyle = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors'
    }
  },
  layers: [
    {
      id: 'osm-base-layer',
      type: 'raster',
      source: 'osm'
    }
  ]
}

export function createProtomapsStyle() {
  const flavor = namedFlavor('light')
  const baseLayers = layers('protomaps', flavor, { lang: 'en' })

  return {
    version: 8,
    glyphs: PROTOMAPS_GLYPHS_URL,
    sprite: PROTOMAPS_SPRITE_URL,
    sources: {
      protomaps: {
        type: 'vector',
        url: `pmtiles://${singaporeTilesUrl}`,
        attribution:
          '<a href="https://protomaps.com" target="_blank">Protomaps</a> © <a href="https://openstreetmap.org" target="_blank">OpenStreetMap</a>'
      },
      buildings: {
        type: 'vector',
        url: `pmtiles://${singaporeBuildingsTilesUrl}`,
        attribution:
          '<a href="https://overturemaps.org" target="_blank">Overture Maps Foundation</a>'
      }
    },
    layers: baseLayers
  }
}
