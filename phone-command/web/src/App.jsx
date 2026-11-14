import React, { useState, useEffect } from 'react'
import { supabase } from './supabaseClient'
import {
  Monitor,
  Camera,
  Activity,
  Globe,
  FileCode,
  Play,
  LogOut,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  X,
  ExternalLink
} from 'lucide-react'

export default function App() {
  const [session, setSession] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState('')

  const [allowedActions, setAllowedActions] = useState([])
  const [commands, setCommands] = useState([])
  const [submittingAction, setSubmittingAction] = useState(null)
  const [screenshotModal, setScreenshotModal] = useState({ isOpen: false, url: null, loading: false, path: null })

  // -------------------------------------------------------------------------
  // Auth Session
  // -------------------------------------------------------------------------
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setAuthLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      setAuthLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [])

  // -------------------------------------------------------------------------
  // Data Fetching & Subscriptions
  // -------------------------------------------------------------------------
  const fetchActionsAndCommands = async () => {
    if (!session) return

    // 1. Fetch allowed actions published by listener
    const { data: actionsData } = await supabase
      .table('allowed_actions')
      .select('*')
      .order('category', { ascending: true })
    if (actionsData) setAllowedActions(actionsData)

    // 2. Fetch recent commands
    const { data: cmdsData } = await supabase
      .table('commands')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(20)
    if (cmdsData) setCommands(cmdsData)
  }

  useEffect(() => {
    if (!session) return
    fetchActionsAndCommands()

    // Realtime subscription for commands updates and allowed_actions
    const commandChannel = supabase
      .channel('public:commands')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'commands' },
        (payload) => {
          if (payload.eventType === 'INSERT') {
            setCommands((prev) => [payload.new, ...prev.filter((c) => c.id !== payload.new.id)])
          } else if (payload.eventType === 'UPDATE') {
            setCommands((prev) => prev.map((c) => (c.id === payload.new.id ? payload.new : c)))
          }
        }
      )
      .subscribe()

    const actionsChannel = supabase
      .channel('public:allowed_actions')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'allowed_actions' },
        () => {
          supabase
            .table('allowed_actions')
            .select('*')
            .order('category', { ascending: true })
            .then(({ data }) => {
              if (data) setAllowedActions(data)
            })
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(commandChannel)
      supabase.removeChannel(actionsChannel)
    }
  }, [session])

  // -------------------------------------------------------------------------
  // Command Dispatcher
  // -------------------------------------------------------------------------
  const handleTriggerAction = async (actionId) => {
    if (!session || submittingAction) return
    setSubmittingAction(actionId)

    try {
      const { error } = await supabase.table('commands').insert({
        action: actionId,
        args: {},
        status: 'pending',
      })
      if (error) {
        alert(`Failed to send command: ${error.message}`)
      }
    } catch (err) {
      alert(`Error: ${err.message}`)
    } finally {
      setSubmittingAction(null)
    }
  }

  // -------------------------------------------------------------------------
  // Screenshot Signed URL Viewer (60 seconds)
  // -------------------------------------------------------------------------
  const handleViewScreenshot = async (filePath) => {
    setScreenshotModal({ isOpen: true, url: null, loading: true, path: filePath })
    try {
      const { data, error } = await supabase.storage
        .from('screenshots')
        .createSignedUrl(filePath, 60)

      if (error || !data?.signedUrl) {
        alert(`Could not generate signed URL: ${error?.message || 'Access denied'}`)
        setScreenshotModal({ isOpen: false, url: null, loading: false, path: null })
      } else {
        setScreenshotModal({ isOpen: true, url: data.signedUrl, loading: false, path: filePath })
      }
    } catch (e) {
      alert(`Storage error: ${e.message}`)
      setScreenshotModal({ isOpen: false, url: null, loading: false, path: null })
    }
  }

  // -------------------------------------------------------------------------
  // Auth Handlers
  // -------------------------------------------------------------------------
  const handleLogin = async (e) => {
    e.preventDefault()
    setAuthError('')
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) setAuthError(error.message)
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    setSession(null)
  }

  // -------------------------------------------------------------------------
  // Status Badge Helper
  // -------------------------------------------------------------------------
  const renderStatusBadge = (status) => {
    if (status === 'pending') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-950/80 text-amber-400 border border-amber-800/60 animate-pulse">
          <Clock className="w-3.5 h-3.5" /> Pending
        </span>
      )
    }
    if (status === 'done') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
          <CheckCircle className="w-3.5 h-3.5" /> Done
        </span>
      )
    }
    if (status?.startsWith('rejected')) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-950/80 text-rose-400 border border-rose-800/60">
          <AlertTriangle className="w-3.5 h-3.5" /> {status}
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-950/80 text-red-400 border border-red-800/60">
        <XCircle className="w-3.5 h-3.5" /> {status || 'Failed'}
      </span>
    )
  }

  const getActionIcon = (id, category) => {
    if (id === 'screenshot') return <Camera className="w-4 h-4 text-sky-400" />
    if (id === 'ping') return <Activity className="w-4 h-4 text-emerald-400" />
    if (category === 'apps') return <Monitor className="w-4 h-4 text-indigo-400" />
    if (category === 'sites') return <Globe className="w-4 h-4 text-teal-400" />
    if (category === 'scripts') return <FileCode className="w-4 h-4 text-purple-400" />
    return <Play className="w-4 h-4 text-slate-400" />
  }

  // -------------------------------------------------------------------------
  // Render: Loading Screen
  // -------------------------------------------------------------------------
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950 text-slate-400">
        <RefreshCw className="w-6 h-6 animate-spin text-sky-500 mr-2" />
        <span>Authenticating...</span>
      </div>
    )
  }

  // -------------------------------------------------------------------------
  // Render: Login Screen
  // -------------------------------------------------------------------------
  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-slate-950">
        <div className="w-full max-w-sm bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur">
          <div className="flex flex-col items-center mb-6">
            <div className="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center mb-3 text-sky-400">
              <Monitor className="w-6 h-6" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white">LYA Command</h1>
            <p className="text-xs text-slate-400 mt-1">Admin access only</p>
          </div>

          {authError && (
            <div className="mb-4 p-3 bg-red-950/70 border border-red-800 text-red-200 text-xs rounded-lg flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition"
                placeholder="admin@example.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              className="w-full mt-2 py-2.5 px-4 rounded-lg bg-sky-600 hover:bg-sky-500 active:bg-sky-700 text-white font-medium text-sm transition shadow-lg shadow-sky-950/50 flex items-center justify-center gap-2"
            >
              Sign In
            </button>
          </form>
        </div>
      </div>
    )
  }

  // Group allowed actions by category
  const categories = ['system', 'apps', 'sites', 'scripts']
  const groupedActions = categories.reduce((acc, cat) => {
    acc[cat] = allowedActions.filter((a) => a.category === cat)
    return acc
  }, {})

  // -------------------------------------------------------------------------
  // Render: Authenticated PWA Interface
  // -------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 pb-20">
      {/* Top Header */}
      <header className="sticky top-0 z-30 bg-slate-950/80 backdrop-blur-md border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Monitor className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white leading-tight">LYA Phone Command</h1>
            <p className="text-[11px] text-slate-400">{session.user.email}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchActionsAndCommands}
            title="Refresh"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleLogout}
            title="Log out"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-red-400 transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      <main className="max-w-md mx-auto px-4 py-5 space-y-6">
        {/* Section 1: Allowed Action Triggers */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Allowed Actions</h2>
            <span className="text-[11px] text-slate-400 font-mono">
              {allowedActions.length} ready
            </span>
          </div>

          {allowedActions.length === 0 ? (
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-center text-slate-400 text-xs">
              Waiting for laptop listener to publish actions...
            </div>
          ) : (
            <div className="space-y-4">
              {categories.map((cat) => {
                const items = groupedActions[cat] || []
                if (items.length === 0) return null
                return (
                  <div key={cat} className="space-y-2">
                    <h3 className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                      {cat}
                    </h3>
                    <div className="grid grid-cols-2 gap-2.5">
                      {items.map((act) => {
                        const isBusy = submittingAction === act.id
                        return (
                          <button
                            key={act.id}
                            disabled={isBusy}
                            onClick={() => handleTriggerAction(act.id)}
                            className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 active:scale-[0.98] transition text-left group disabled:opacity-50"
                          >
                            <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 group-hover:border-slate-700">
                              {getActionIcon(act.id, act.category)}
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-medium text-slate-200 truncate">{act.label}</p>
                              <p className="text-[10px] text-slate-400 font-mono truncate">{act.id}</p>
                            </div>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>

        {/* Section 2: Command History & Live Status */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Activity Log</h2>
            <span className="text-[11px] text-slate-400 font-mono">{commands.length} records</span>
          </div>

          <div className="space-y-2.5">
            {commands.length === 0 ? (
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-center text-slate-400 text-xs">
                No commands dispatched yet. Tap an action button above.
              </div>
            ) : (
              commands.map((cmd) => {
                const isScreenshotDone = cmd.action === 'screenshot' && cmd.status === 'done' && cmd.result
                return (
                  <div
                    key={cmd.id}
                    className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xs font-semibold text-white truncate font-mono">
                          {cmd.action}
                        </span>
                      </div>
                      <div>{renderStatusBadge(cmd.status)}</div>
                    </div>

                    {cmd.result && (
                      <div className="text-xs font-mono text-slate-300 bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/80 break-words whitespace-pre-wrap max-h-36 overflow-y-auto">
                        {cmd.result}
                      </div>
                    )}

                    <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-1">
                      <span>{new Date(cmd.created_at).toLocaleTimeString()}</span>
                      {isScreenshotDone && (
                        <button
                          onClick={() => handleViewScreenshot(cmd.result)}
                          className="inline-flex items-center gap-1 text-sky-400 hover:text-sky-300 transition underline underline-offset-2"
                        >
                          <Camera className="w-3.5 h-3.5" /> View Screenshot
                        </button>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </section>
      </main>

      {/* Screenshot Viewer Modal */}
      {screenshotModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
              <span className="text-xs font-medium text-slate-300 flex items-center gap-1.5 font-mono">
                <Camera className="w-3.5 h-3.5 text-sky-400" /> 60s Signed Screenshot
              </span>
              <button
                onClick={() => setScreenshotModal({ isOpen: false, url: null, loading: false, path: null })}
                className="p-1 rounded-md text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 flex-1 flex items-center justify-center overflow-auto bg-slate-950 min-h-[220px]">
              {screenshotModal.loading ? (
                <div className="flex flex-col items-center gap-2 text-slate-400 text-xs">
                  <RefreshCw className="w-5 h-5 animate-spin text-sky-500" />
                  <span>Generating signed URL...</span>
                </div>
              ) : screenshotModal.url ? (
                <img
                  src={screenshotModal.url}
                  alt="Laptop Screenshot"
                  className="max-w-full max-h-[70vh] rounded-lg border border-slate-800 object-contain shadow-lg"
                />
              ) : (
                <span className="text-xs text-red-400">Failed to load preview</span>
              )}
            </div>

            {screenshotModal.url && (
              <div className="px-4 py-2.5 bg-slate-900 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                <span>Expires in 60 seconds</span>
                <a
                  href={screenshotModal.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sky-400 hover:underline flex items-center gap-1"
                >
                  Full image <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
