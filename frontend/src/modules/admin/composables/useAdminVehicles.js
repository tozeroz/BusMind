import { computed, onMounted, reactive, ref } from 'vue'
import { getLineStations } from '@/api/transit'
import { getVehicleDetail, getVehicles } from '@/api/vehicle'
import { getApiErrorMessage, unwrapData, unwrapList } from '@/api/response'

const PAGE_SIZE = 100
const normalizeStation = (item) => ({ ...item, ...(item.station || {}) })

export function useAdminVehicles() {
  const filters = reactive({ keyword: '' })
  const vehicles = ref([])
  const selectedVehicle = ref(null)
  const routeStations = ref([])
  const loading = ref(false)
  const detailLoading = ref(false)
  const errorMessage = ref('')
  const stationCache = new Map()

  const filteredVehicles = computed(() => {
    const keyword = filters.keyword.trim().toLowerCase()
    if (!keyword) return vehicles.value
    return vehicles.value.filter((vehicle) => [vehicle.vehicle_code, vehicle.vehicle_id]
      .filter((value) => value !== null && value !== undefined)
      .some((value) => String(value).toLowerCase().includes(keyword)))
  })

  async function loadVehicles() {
    loading.value = true
    errorMessage.value = ''
    try {
      const firstResponse = await getVehicles({ page: 1, limit: PAGE_SIZE })
      const firstItems = unwrapList(firstResponse, 'vehicles')
      const total = Number(firstResponse?.data?.total ?? firstItems.length)
      const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
      const remaining = pageCount > 1
        ? await Promise.all(Array.from({ length: pageCount - 1 }, (_, index) =>
          getVehicles({ page: index + 2, limit: PAGE_SIZE })))
        : []
      vehicles.value = [firstItems, ...remaining.map((response) => unwrapList(response, 'vehicles'))]
        .flat()
        .filter((vehicle) => vehicle?.vehicle_id)
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '\u8f66\u8f86\u6570\u636e\u52a0\u8f7d\u5931\u8d25')
    } finally {
      loading.value = false
    }
  }

  async function getStations(lineId) {
    if (!Number.isFinite(Number(lineId))) return []
    if (stationCache.has(lineId)) return stationCache.get(lineId)
    const response = await getLineStations(lineId)
    const stations = unwrapList(response, 'stations')
      .map(normalizeStation)
      .sort((a, b) => Number(a.order_index ?? a.stop_sequence ?? 0) - Number(b.order_index ?? b.stop_sequence ?? 0))
    stationCache.set(lineId, stations)
    return stations
  }

  async function selectVehicle(vehicle) {
    detailLoading.value = true
    errorMessage.value = ''
    try {
      const detailResponse = await getVehicleDetail(vehicle.vehicle_id)
      const detail = { ...vehicle, ...unwrapData(detailResponse, {}) }
      selectedVehicle.value = detail
      routeStations.value = await getStations(detail.line_id)
    } catch (error) {
      selectedVehicle.value = { ...vehicle }
      routeStations.value = await getStations(vehicle.line_id).catch(() => [])
      errorMessage.value = getApiErrorMessage(error, '\u8f66\u8f86\u8be6\u60c5\u52a0\u8f7d\u5931\u8d25')
    } finally {
      detailLoading.value = false
    }
  }

  onMounted(loadVehicles)

  return {
    filters, vehicles, filteredVehicles, selectedVehicle, routeStations,
    loading, detailLoading, errorMessage, loadVehicles, selectVehicle
  }
}
