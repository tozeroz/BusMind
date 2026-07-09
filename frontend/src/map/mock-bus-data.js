export const mockBusStops = [
  {
    stop_id: 'S001',
    stop_name: '乌节站',
    lng: 103.8319,
    lat: 1.3042,
    eta_minutes: 4,
    crowd_level: 'medium',
    passing_routes: ['市中心环线', '滨海快线']
  },
  {
    stop_id: 'S002',
    stop_name: '索美塞站',
    lng: 103.8395,
    lat: 1.3009,
    eta_minutes: 6,
    crowd_level: 'low',
    passing_routes: ['市中心环线', '舒适支线']
  },
  {
    stop_id: 'S003',
    stop_name: '多美歌站',
    lng: 103.8466,
    lat: 1.2991,
    eta_minutes: 8,
    crowd_level: 'medium',
    passing_routes: ['市中心环线', '滨海快线', '舒适支线']
  },
  {
    stop_id: 'S004',
    stop_name: '市政厅站',
    lng: 103.8522,
    lat: 1.2931,
    eta_minutes: 5,
    crowd_level: 'high',
    passing_routes: ['市中心环线', '晚高峰支线']
  },
  {
    stop_id: 'S005',
    stop_name: '莱佛士坊站',
    lng: 103.8517,
    lat: 1.2848,
    eta_minutes: 10,
    crowd_level: 'high',
    passing_routes: ['滨海快线', '晚高峰支线']
  },
  {
    stop_id: 'S006',
    stop_name: '滨海湾站',
    lng: 103.859,
    lat: 1.2806,
    eta_minutes: 12,
    crowd_level: 'low',
    passing_routes: ['滨海快线']
  },
  {
    stop_id: 'S007',
    stop_name: '克拉码头站',
    lng: 103.8467,
    lat: 1.2888,
    eta_minutes: 7,
    crowd_level: 'medium',
    passing_routes: ['舒适支线', '晚高峰支线']
  }
]

export const mockBusStopsGeoJSON = {
  type: 'FeatureCollection',
  features: mockBusStops.map((stop) => ({
    type: 'Feature',
    id: stop.stop_id,
    properties: {
      stop_id: stop.stop_id,
      stop_name: stop.stop_name,
      eta_minutes: stop.eta_minutes,
      crowd_level: stop.crowd_level,
      passing_routes: stop.passing_routes.join(',')
    },
    geometry: {
      type: 'Point',
      coordinates: [stop.lng, stop.lat]
    }
  }))
}

export const mockRoutes = [
  {
    line_id: 'L001',
    line_name: '市中心环线',
    crowd_level: 'medium',
    eta_minutes: 8,
    status: '运行正常',
    chart: [44, 62, 78, 66, 58],
    coordinates: [
      [103.8319, 1.3042],
      [103.8356, 1.3025],
      [103.8395, 1.3009],
      [103.8466, 1.2991],
      [103.8506, 1.2964],
      [103.8522, 1.2931],
      [103.8495, 1.2904],
      [103.8467, 1.2888],
      [103.8448, 1.2927],
      [103.8466, 1.2991],
      [103.8395, 1.3009],
      [103.8319, 1.3042]
    ]
  },
  {
    line_id: 'L002',
    line_name: '滨海快线',
    crowd_level: 'low',
    eta_minutes: 10,
    status: '客流舒适',
    chart: [24, 32, 38, 35, 30],
    coordinates: [
      [103.8319, 1.3042],
      [103.8395, 1.3009],
      [103.8466, 1.2991],
      [103.8522, 1.2931],
      [103.8517, 1.2848],
      [103.8552, 1.2822],
      [103.859, 1.2806]
    ]
  },
  {
    line_id: 'L003',
    line_name: '晚高峰支线',
    crowd_level: 'high',
    eta_minutes: 12,
    status: '拥挤，建议错峰',
    chart: [66, 74, 88, 92, 84],
    coordinates: [
      [103.8467, 1.2888],
      [103.8502, 1.2866],
      [103.8517, 1.2848],
      [103.8534, 1.289],
      [103.8522, 1.2931]
    ]
  },
  {
    line_id: 'L004',
    line_name: '舒适支线',
    crowd_level: 'low',
    eta_minutes: 9,
    status: '座位较充足',
    chart: [28, 35, 40, 37, 31],
    coordinates: [
      [103.8395, 1.3009],
      [103.8432, 1.3001],
      [103.8466, 1.2991],
      [103.8495, 1.2948],
      [103.8467, 1.2888]
    ]
  }
]

export const mockBusRouteGeoJSON = {
  type: 'FeatureCollection',
  features: mockRoutes.map((route) => ({
    type: 'Feature',
    id: route.line_id,
    properties: {
      line_id: route.line_id,
      line_name: route.line_name,
      crowd_level: route.crowd_level,
      eta_minutes: route.eta_minutes,
      status: route.status,
      chart: route.chart.join(',')
    },
    geometry: {
      type: 'LineString',
      coordinates: route.coordinates
    }
  }))
}
