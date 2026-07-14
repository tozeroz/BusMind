import { computed, onMounted, reactive, ref } from 'vue'
import { getLineDetail, getLines, getLineStations } from '@/api/transit'
import { getApiErrorMessage, unwrapData, unwrapList } from '@/api/response'

const PAGE_SIZE = 100

const lineSearchText = (line) => [line.line_name, line.line_code, line.service_no]
  .filter(Boolean)
  .join(' ')
  .toLowerCase()

export function useAdminLines() {
  const filters = reactive({ operator: '', station: '', keyword: '' })
  const allLines = ref([])
  const filteredLines = ref([])
  const selectedLine = ref(null)
  const selectedStations = ref([])
  const loading = ref(false)
  const filtering = ref(false)
  const detailLoading = ref(false)
  const errorMessage = ref('')
  const stationCache = new Map()

  const operators = computed(() => [...new Set(allLines.value.map((line) => line.operator).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b)))

  const orderedLines = computed(() => {
    if (!selectedLine.value) return filteredLines.value
    return [selectedLine.value, ...filteredLines.value.filter(
      (line) => String(line.line_id) !== String(selectedLine.value.line_id)
    )]
  })

  async function loadAllLines() {
    loading.value = true
    errorMessage.value = ''
    try {
      const firstResponse = await getLines({ page: 1, limit: PAGE_SIZE })
      const firstLines = unwrapList(firstResponse, 'lines')
      const total = Number(firstResponse?.data?.total ?? firstLines.length)
      const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
      const remainingResponses = pageCount > 1
        ? await Promise.all(Array.from({ length: pageCount - 1 }, (_, index) =>
          getLines({ page: index + 2, limit: PAGE_SIZE })))
        : []
      allLines.value = [firstLines, ...remainingResponses.map((response) => unwrapList(response, 'lines'))]
        .flat()
        .filter((line) => line?.line_id)
      filteredLines.value = [...allLines.value]
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '\u7ebf\u8def\u6570\u636e\u52a0\u8f7d\u5931\u8d25')
    } finally {
      loading.value = false
    }
  }

  async function getStationsForLine(lineId) {
    if (stationCache.has(lineId)) return stationCache.get(lineId)
    const response = await getLineStations(lineId)
    const stations = unwrapList(response, 'stations')
      .map((item) => ({ ...item, ...(item.station || {}) }))
    stationCache.set(lineId, stations)
    return stations
  }

  async function applyFilters() {
    filtering.value = true
    errorMessage.value = ''
    selectedLine.value = null
    selectedStations.value = []
    try {
      const operator = filters.operator.trim().toLowerCase()
      const keyword = filters.keyword.trim().toLowerCase()
      const station = filters.station.trim().toLowerCase()
      let matches = allLines.value.filter((line) => {
        const operatorMatches = !operator || String(line.operator || '').toLowerCase().includes(operator)
        const keywordMatches = !keyword || lineSearchText(line).includes(keyword)
        return operatorMatches && keywordMatches
      })
      if (station) {
        const stationResults = await Promise.all(matches.map(async (line) => ({
          line,
          stations: await getStationsForLine(line.line_id)
        })))
        matches = stationResults.filter(({ stations }) => stations.some((item) =>
          String(item.station_name || item.stop_name || item.station_code || '').toLowerCase().includes(station)
        )).map(({ line }) => line)
      }
      filteredLines.value = matches
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '\u7ebf\u8def\u7b5b\u9009\u5931\u8d25')
    } finally {
      filtering.value = false
    }
  }

  function resetFilters() {
    Object.assign(filters, { operator: '', station: '', keyword: '' })
    selectedLine.value = null
    selectedStations.value = []
    filteredLines.value = [...allLines.value]
  }

  async function selectLine(line) {
    detailLoading.value = true
    errorMessage.value = ''
    try {
      const [detailResponse, stations] = await Promise.all([
        getLineDetail(line.line_id),
        getStationsForLine(line.line_id)
      ])
      selectedLine.value = { ...line, ...unwrapData(detailResponse, {}) }
      selectedStations.value = stations
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '\u7ebf\u8def\u8be6\u60c5\u52a0\u8f7d\u5931\u8d25')
    } finally {
      detailLoading.value = false
    }
  }

  onMounted(loadAllLines)

  return {
    filters, allLines, filteredLines, orderedLines, selectedLine, selectedStations,
    operators, loading, filtering, detailLoading, errorMessage,
    loadAllLines, applyFilters, resetFilters, selectLine
  }
}
