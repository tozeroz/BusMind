export const crowdClass = (level) => {
  const map = {
    空闲: 'level-free',
    适中: 'level-normal',
    拥挤: 'level-busy',
    非常拥挤: 'level-full'
  }
  return map[level] || 'level-normal'
}
