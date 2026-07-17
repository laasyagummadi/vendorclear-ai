import '@testing-library/jest-dom'

// jsdom has no canvas 2D context implementation, which Chart.js needs.
// Stub it so Dashboard.jsx (which renders Chart.js doughnut/bar/line
// charts) can mount without throwing "getContext is not a function".
HTMLCanvasElement.prototype.getContext = () => ({
  clearRect: () => {}, fillRect: () => {}, beginPath: () => {}, arc: () => {},
  fill: () => {}, stroke: () => {}, moveTo: () => {}, lineTo: () => {},
  closePath: () => {}, save: () => {}, restore: () => {}, translate: () => {},
  scale: () => {}, measureText: () => ({ width: 0 }), fillText: () => {},
  createLinearGradient: () => ({ addColorStop: () => {} }),
  setLineDash: () => {}, getLineDash: () => [],
})

window.scrollTo = () => {}
