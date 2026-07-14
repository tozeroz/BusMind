import { computed, onMounted, reactive, ref } from 'vue'
import { getPassengerFlowPrediction, getPassengerFlowTrend } from '@/api/history'
import { getStations } from '@/api/transit'
import { getApiErrorMessage, unwrapData, unwrapList } from '@/api/response'

const PAGE_SIZE = 100
const emptySummary = () => ({
  total_tap_in: 0,
  total_tap_out: 0,
  total_flow: 0,
  dominant_flow_level: null,
  peak_hour: null,
  peak_flow: null,
  point_count: 0
})

export function useAdminPassengerFlow() {
  const filters = reactive({ keyword: '' })
  const stations = ref([])
  const selectedStation = ref(null)
  const trendItems = ref([])
  const predictionItems = ref([])
  const summary = ref(emptySummary())
  const stationLoading = ref(false)
  const detailLoading = ref(false)
  const errorMessage = ref('')

  const filteredStations = computed(() => {
    const keyword = filters.keyword.trim().toLowerCase()
    if (!keyword) return stations.value
    return stations.value.filter((station) => [
      station.station_name,
      station.station_code,
      station.bus_stop_code,
      station.road_name,
      station.address
    ].filter(Boolean).some((value) => String(value).toLowerCase().includes(keyword)))
  })

  async function loadStations() {
    stationLoading.value = true
    errorMessage.value = ''
    try {
      const firstResponse = await getStations({ page: 1, limit: PAGE_SIZE })
      const firstItems = unwrapList(firstResponse, 'stations')
      const total = Number(unwrapData(firstResponse, {})?.total ?? firstItems.length)
      const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
      const remaining = pageCount > 1
        ? await Promise.all(Array.from({ length: pageCount - 1 }, (_, index) =>
          getStations({ page: index + 2, limit: PAGE_SIZE })))
        : []
      stations.value = [firstItems, ...remaining.map((response) => unwrapList(response, 'stations'))]
        .flat()
        .filter((station) => station?.station_id)
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '\u7ad9\u70b9\u5217\u8868\u52a0\u8f7d\u5931\u8d25')
    } finally {
      stationLoading.value = false
    }
  }

  async function selectStation(station) {
    selectedStation.value = station
    trendItems.value = []
    predictionItems.value = []
    summary.value = emptySummary()
    detailLoading.value = true
    errorMessage.value = ''
    try {
      const [trendResponse, predictionResponse] = await Promise.all([
        getPassengerFlowTrend({ station_id: station.station_id, granularity: 'hour' }),
        getPassengerFlowPrediction({ target_type: 'station', target_id: String(station.station_id) })
      ])
      const trend = unwrapData(trendResponse, {})
      trendItems.value = Array.isArray(trend.items) ? trend.items : []
      summary.value = { ...emptySummary(), ...(trend.summary || {}) }
      predictionItems.value = unwrapList(predictionResponse, 'items')
        .slice()
        .sort((a, b) => new Date(a.predict_time) - new Date(b.predict_time))
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '\u5ba2\u6d41\u8be6\u60c5\u52a0\u8f7d\u5931\u8d25')
    } finally {
      detailLoading.value = false
    }
  }

  onMounted(loadStations)

  return {
    filters,
    stations,
    filteredStations,
    selectedStation,
    trendItems,
    predictionItems,
    summary,
    stationLoading,
    detailLoading,
    errorMessage,
    loadStations,
    selectStation
  }
}
