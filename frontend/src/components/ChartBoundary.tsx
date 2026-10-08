import { Component, type ReactNode } from 'react'

/** If a chart throws while rendering, drop just the chart; the message and its tables stay. */
export class ChartBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? null : this.props.children
  }
}
