import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Mock } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

const { apiGet, apiPost, apiPatch, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}))

vi.mock('../../api/client', () => ({
  api: {
    get: apiGet,
    post: apiPost,
    patch: apiPatch,
    delete: apiDelete,
  },
}))

import type { ConnectorTokenSummary } from '../../api/client'
import { Settings } from '../Settings'

const SETTINGS_RESPONSE = {
  timezone: 'UTC',
  transcript_enabled: true,
  crisis_disclaimer_acknowledged_at: null,
}

const ACTIVE_TOKEN: ConnectorTokenSummary = {
  id: 'tok-active-1',
  created_at: '2026-04-01T00:00:00Z',
  last_used_at: null,
  expires_at: '2026-08-01T00:00:00Z',
  revoked_at: null,
}

const REVOKED_TOKEN: ConnectorTokenSummary = {
  id: 'tok-revoked-1',
  created_at: '2026-03-01T00:00:00Z',
  last_used_at: '2026-04-15T12:00:00Z',
  expires_at: '2026-06-01T00:00:00Z',
  revoked_at: '2026-04-20T09:00:00Z',
}

const mockEndpoints = (tokens: ConnectorTokenSummary[] = []) => {
  apiGet.mockImplementation(async (path: string) => {
    if (path === '/settings') return SETTINGS_RESPONSE
    if (path === '/connect/tokens') return tokens
    throw new Error(`unexpected GET ${path}`)
  })
}

describe('Settings — connector tokens section', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPatch.mockReset()
    apiDelete.mockReset()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the empty state when there are no tokens', async () => {
    mockEndpoints([])
    render(<Settings />)
    expect(await screen.findByText(/no tokens yet/i)).toBeInTheDocument()
  })

  it('renders the spec page title', async () => {
    mockEndpoints([])
    render(<Settings />)
    expect(
      await screen.findByRole('heading', { name: /^Settings$/i }),
    ).toBeInTheDocument()
  })

  it('toggling Save transcripts patches /settings with transcript_enabled', async () => {
    mockEndpoints([])
    apiPatch.mockResolvedValueOnce({
      ...SETTINGS_RESPONSE,
      transcript_enabled: false,
    })

    render(<Settings />)

    const label = await screen.findByText(/On — summary \+ transcript/i)
    fireEvent.click(label.closest('label')!)

    await waitFor(() => {
      expect(apiPatch).toHaveBeenCalledWith('/settings', {
        transcript_enabled: false,
      })
    })
  })

  it('renders an active token row with status, created date, and last used', async () => {
    mockEndpoints([ACTIVE_TOKEN])
    render(<Settings />)
    expect(await screen.findByText(/Active/)).toBeInTheDocument()
    expect(screen.getByText(/Last used never/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /^Revoke$/ }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Revoke and reissue/i }),
    ).toBeInTheDocument()
  })

  it('renders a revoked token row without action buttons', async () => {
    mockEndpoints([REVOKED_TOKEN])
    render(<Settings />)
    expect(await screen.findByText(/Revoked/)).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /^Revoke$/ }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Revoke and reissue/i }),
    ).not.toBeInTheDocument()
  })

  it('revokes a token and refreshes the list', async () => {
    mockEndpoints([ACTIVE_TOKEN])
    apiPost.mockResolvedValueOnce({})

    render(<Settings />)
    const revokeButton = await screen.findByRole('button', { name: /^Revoke$/ })

    fireEvent.click(revokeButton)

    await waitFor(() => {
      expect(apiPost).toHaveBeenCalledWith(
        `/connect/tokens/${ACTIVE_TOKEN.id}/revoke`,
      )
    })
    // /settings on initial load + /connect/tokens on initial load + refresh
    await waitFor(() => {
      const tokenCalls = (apiGet as Mock).mock.calls.filter(
        (c) => c[0] === '/connect/tokens',
      )
      expect(tokenCalls.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('reissues a token and surfaces the new value', async () => {
    mockEndpoints([ACTIVE_TOKEN])
    apiPost
      .mockResolvedValueOnce({}) // revoke
      .mockResolvedValueOnce({
        // mint
        token: 'kdr_new_token_value_12345',
        created_at: '2026-05-04T00:00:00Z',
        expires_at: '2026-08-02T00:00:00Z',
      })

    render(<Settings />)
    const reissueButton = await screen.findByRole('button', {
      name: /Revoke and reissue/i,
    })

    fireEvent.click(reissueButton)

    await waitFor(() => {
      expect(apiPost).toHaveBeenNthCalledWith(
        1,
        `/connect/tokens/${ACTIVE_TOKEN.id}/revoke`,
      )
    })
    await waitFor(() => {
      expect(apiPost).toHaveBeenNthCalledWith(2, '/connect/token')
    })
    expect(
      await screen.findByText(/kdr_new_token_value_12345/),
    ).toBeInTheDocument()
  })
})
