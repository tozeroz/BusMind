/**
 * 定位按钮可使用的固定站点坐标。
 * latitude 为纬度，longitude 为经度，radiusKm 为附近站点搜索半径。
 */
export const LOCATION_PRESETS = Object.freeze({
  // 63061：Opp Blk 25
  oppBlk25: Object.freeze({
    name: 'Opp Blk 25',
    latitude: 1.36623834226067,
    longitude: 103.89129134480065,
    radiusKm: 2
  }),

  // 66011：Aft Braddell Rd
  aftBraddellRd: Object.freeze({
    name: 'Aft Braddell Rd',
    latitude: 1.34716997902419,
    longitude: 103.8599767808637,
    radiusKm: 2
  }),

  // 66019：Bef Braddell Rd
  befBraddellRd: Object.freeze({
    name: 'Bef Braddell Rd',
    latitude: 1.34602837489201,
    longitude: 103.86040421534554,
    radiusKm: 2
  }),

  // 66021：New Tech Pk
  newTechPk: Object.freeze({
    name: 'New Tech Pk',
    latitude: 1.35096671417894,
    longitude: 103.86182938341672,
    radiusKm: 2
  }),

  // 66029：St. Gabriel's Pr Sch
  stGabrielsPrSch: Object.freeze({
    name: "St. Gabriel's Pr Sch",
    latitude: 1.35017159420349,
    longitude: 103.86143525134639,
    radiusKm: 2
  }),

  // 66399：Lor Chuan Stn
  lorChuanStn: Object.freeze({
    name: 'Lor Chuan Stn',
    latitude: 1.35148729748638,
    longitude: 103.8632462430678,
    radiusKm: 2
  })
})

// 当前启用的固定位置。切换站点时只需修改这里的预设名称。
export const INJECTED_LOCATION = LOCATION_PRESETS.oppBlk25
