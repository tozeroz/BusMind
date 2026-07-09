export const mockBusStops = [
  {
    stop_id: 'S001',
    stop_name: 'Raffles Place',
    lng: 103.8519,
    lat: 1.2847,
    eta_minutes: 5,
    crowd_level: 'low',
    passing_routes: ['10', '57', '70M']
  },
  {
    stop_id: 'S002',
    stop_name: 'City Hall',
    lng: 103.8521,
    lat: 1.2931,
    eta_minutes: 8,
    crowd_level: 'medium',
    passing_routes: ['36', '77', '106']
  },
  {
    stop_id: 'S003',
    stop_name: 'Bugis',
    lng: 103.8556,
    lat: 1.3008,
    eta_minutes: 12,
    crowd_level: 'high',
    passing_routes: ['7', '12', '197']
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

export const mockBusRouteGeoJSON = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      id: 'L001',
      properties: {
        line_id: 'L001',
        line_name: 'Demo Bus Line',
        crowd_level: 'medium'
      },
      geometry: {
        type: 'LineString',
        coordinates: [
          [103.8519, 1.2847],
          [103.8521, 1.2931],
          [103.8556, 1.3008]
        ]
      }
    }
  ]
}
