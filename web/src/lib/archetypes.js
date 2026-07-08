// archetype → color + Lucide icon name + short gloss (no emoji anywhere)
export const ARCH = {
  '지식인':   { color: '#6ea8fe', icon: 'BrainCircuit', gloss: '공감·답변으로 인정받는 해결사' },
  '인기인':   { color: '#f0b866', icon: 'Star',         gloss: '받은 공감 총량 최상위' },
  '싸움꾼':   { color: '#ef6f6f', icon: 'Swords',       gloss: '논쟁·반박 비율이 높은 사람' },
  '질문러':   { color: '#7ee0c0', icon: 'HelpCircle',   gloss: '질문을 가장 많이 던지는 사람' },
  '인싸':     { color: '#c88bf0', icon: 'Users',        gloss: '대화 상대 폭이 가장 넓음' },
  '수다왕':   { color: '#f08bb4', icon: 'MessagesSquare', gloss: '순수 발언량 최상위' },
  '유머러':   { color: '#f0d066', icon: 'Laugh',        gloss: 'ㅋㅋ·웃음 비율이 높음' },
  '홍보러':   { color: '#9fd06e', icon: 'Megaphone',    gloss: '링크·모집·홍보가 잦음' },
  '미디어러': { color: '#6ec6f0', icon: 'Image',        gloss: '사진·파일 공유 비율 높음' },
  '야행성':   { color: '#8b95cf', icon: 'Moon',         gloss: '새벽 시간대 활동 집중' },
}
export const archColor = (a) => (ARCH[a]?.color) || '#8b95a9'
export const archIcon = (a) => (ARCH[a]?.icon) || 'Circle'
