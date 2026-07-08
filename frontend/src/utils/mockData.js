export const lines = [
  {
    id: '1',
    name: '校园 1 号线',
    start: '北门',
    end: '南门',
    time: '07:00 - 22:00',
    vehicles: 4,
    wait: 6,
    crowd: '拥挤',
    stations: ['北门', '宿舍区', '食堂', '教学楼', '图书馆', '体育馆', '南门']
  },
  {
    id: '2',
    name: '校园 2 号线',
    start: '地铁站',
    end: '东门',
    time: '06:50 - 22:30',
    vehicles: 5,
    wait: 8,
    crowd: '适中',
    stations: ['地铁站', '西门', '实验楼', '教学楼', '行政楼', '东门']
  },
  {
    id: '3',
    name: '校园 3 号线',
    start: '学生公寓',
    end: '地铁站',
    time: '07:10 - 21:40',
    vehicles: 3,
    wait: 10,
    crowd: '空闲',
    stations: ['学生公寓', '医务室', '食堂', '图书馆', '创新楼', '地铁站']
  }
]

export const vehicles = [
  { id: 'A102', line: '校园 1 号线', position: '宿舍区 → 食堂', next: '食堂', eta: 4, passengers: 52, capacity: 70, crowd: '拥挤', status: '正常' },
  { id: 'A118', line: '校园 1 号线', position: '教学楼 → 图书馆', next: '图书馆', eta: 7, passengers: 61, capacity: 70, crowd: '非常拥挤', status: '正常' },
  { id: 'B205', line: '校园 2 号线', position: '西门 → 实验楼', next: '实验楼', eta: 5, passengers: 35, capacity: 70, crowd: '适中', status: '正常' },
  { id: 'C306', line: '校园 3 号线', position: '医务室 → 食堂', next: '食堂', eta: 9, passengers: 20, capacity: 70, crowd: '空闲', status: '延误' }
]

export const flowRows = [
  { time: '07:00', line1: 68, line2: 54, line3: 39 },
  { time: '09:00', line1: 82, line2: 61, line3: 45 },
  { time: '12:00', line1: 74, line2: 66, line3: 58 },
  { time: '17:00', line1: 90, line2: 72, line3: 63 },
  { time: '20:00', line1: 47, line2: 38, line3: 31 }
]

export const hotStations = [
  { name: '教学楼', count: 1280 },
  { name: '宿舍区', count: 1160 },
  { name: '食堂', count: 980 },
  { name: '图书馆', count: 830 },
  { name: '地铁站', count: 760 }
]

export const adminStats = [
  { label: '线路数量', value: '3 条' },
  { label: '站点数量', value: '18 个' },
  { label: '在线车辆', value: '12 辆' },
  { label: '今日客流', value: '5010 人次' }
]
