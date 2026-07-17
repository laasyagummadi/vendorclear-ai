import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import Toast from '../components/Toast.jsx'

describe('Toast', () => {
  it('renders with {id,msg,type,onRemove} props without throwing (regression: previously expected {toasts,setToasts} and crashed on every toast)', () => {
    expect(() =>
      render(<Toast id={1} msg="Vendor created successfully!" type="success" onRemove={vi.fn()} />)
    ).not.toThrow()
    expect(screen.getByText('Vendor created successfully!')).toBeInTheDocument()
  })

  it('calls onRemove after the auto-dismiss timeout', async () => {
    vi.useFakeTimers()
    const onRemove = vi.fn()
    render(<Toast id={42} msg="Hi" type="error" onRemove={onRemove} />)
    vi.advanceTimersByTime(3600)
    expect(onRemove).toHaveBeenCalledWith(42)
    vi.useRealTimers()
  })

  it('rendering a list the way App.jsx does (one <Toast> per toast) never throws', () => {
    const toasts = [
      { id: 1, msg: 'One', type: 'success' },
      { id: 2, msg: 'Two', type: 'error' },
    ]
    expect(() =>
      render(
        <div>
          {toasts.map(t => <Toast key={t.id} {...t} onRemove={vi.fn()} />)}
        </div>
      )
    ).not.toThrow()
    expect(screen.getByText('One')).toBeInTheDocument()
    expect(screen.getByText('Two')).toBeInTheDocument()
  })
})
