// Stub harness for named Claude Code Workflows.
//
// A workflow file is not a module: it has no imports, it uses top-level await and a
// top-level return, and its API (agent, parallel, pipeline, phase, log, args, budget,
// workflow) is injected by the runtime. So it cannot be imported. It is loaded as TEXT
// and wrapped in an AsyncFunction whose parameters are those injected names, which is the
// closest reproduction of the real runtime that is available offline.

import { readFileSync } from 'node:fs'

const AsyncFunction = (async function () {}).constructor

/** Load a workflow file as a callable AsyncFunction. */
export function loadWorkflow(sourcePath) {
  const raw = readFileSync(sourcePath, 'utf8')
  const src = raw.replace(/^export\s+const\s+meta\s*=/m, 'const meta =')
  return new AsyncFunction(
    'agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow',
    src,
  )
}

/**
 * Evaluate only the exported meta literal, without running the workflow.
 *
 * The regex terminates at the first closing brace in column 0, so meta's nested entries
 * must stay indented. A nested closing brace at column 0 would silently truncate the match.
 */
export function readMeta(sourcePath) {
  const raw = readFileSync(sourcePath, 'utf8')
  const match = raw.match(/^export const meta = (\{[\s\S]*?^\})/m)
  if (!match) throw new Error(`no exported meta literal found in ${sourcePath}`)
  const literal = match[1]
  if (/[^\\]`|\$\{|\.\.\.|\w\s*\(/.test(literal.replace(/'[^']*'/g, "''"))) {
    throw new Error('meta must be a pure literal: no template interpolation, spreads or calls')
  }
  return new Function(`return (${literal})`)()
}

/**
 * Minimal structural check of a value against a JSON Schema. Required keys, closed enums and
 * a nullable `type: [..., 'null']` union - no dependency, no format, no nested oneOf. It
 * exists so a test fixture that drifts from a schema fails in the test rather than in
 * production, where the real runtime would make the model retry. Exported because the event
 * shape is validated by the suite rather than by an `agent()` call: `CONFIG.schemas.event`
 * describes a record the workflow writes itself, so nothing would ever pass it to a model.
 */
export function checkSchema(value, schema, path = '$') {
  if (Array.isArray(schema && schema.type)) {
    if (value === null && schema.type.includes('null')) return []
    const primary = schema.type.filter((t) => t !== 'null')[0]
    return checkSchema(value, { ...schema, type: primary }, path)
  }
  if (!schema || typeof schema !== 'object') return []
  const problems = []
  if (schema.type === 'object') {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) {
      return [`${path} is not an object`]
    }
    for (const key of (schema.required || [])) {
      if (value[key] === undefined) problems.push(`${path}.${key} is required and missing`)
    }
    for (const [key, sub] of Object.entries(schema.properties || {})) {
      if (value[key] !== undefined) problems.push(...checkSchema(value[key], sub, `${path}.${key}`))
    }
    return problems
  }
  if (schema.type === 'array') {
    if (!Array.isArray(value)) return [`${path} is not an array`]
    if (schema.minItems !== undefined && value.length < schema.minItems) {
      problems.push(`${path} has ${value.length} items, minItems ${schema.minItems}`)
    }
    value.forEach((item, i) => problems.push(...checkSchema(item, schema.items, `${path}[${i}]`)))
    return problems
  }
  if (Array.isArray(schema.enum) && !schema.enum.includes(value)) {
    problems.push(`${path} value ${JSON.stringify(value)} is not in enum ${JSON.stringify(schema.enum)}`)
  }
  return problems
}

/**
 * Build the injected stubs.
 *
 * responders maps an agent label to a canned return value or to a function
 * (call, allCallsSoFar) => value. A key ending in "*" matches by prefix; the longest
 * matching prefix wins, and an exact key always beats a prefix key. An agent whose label
 * has no responder throws, so a new agent() call added to the workflow can never pass a
 * test silently. A responder that returns null is legal and models the documented case
 * where the user skips an agent or the subagent dies after retries.
 *
 * budgetTotal set to a number models the runtime's hard token ceiling: agent() throws once
 * the simulated spend reaches it, exactly as the contract describes.
 *
 * runtimeCap models the RUNTIME's own concurrency limit (min(16, CPUs - 2)): excess calls
 * QUEUE, they do not fail. That distinction matters for what the suite can prove. If the
 * harness threw at the workflow's own chunk size instead, the concurrency test would be
 * asserting that the harness enforces the cap, which is circular. With a queue at 16 and a
 * chunk size of 2 or 4, `maxInFlight` measures what the WORKFLOW's chunking actually holds.
 */
export function makeHarness({
  responders = {},
  runtimeCap = 16,
  tickMs = 0,
  budgetTotal = null,
  tokensPerAgent = 1000,
} = {}) {
  const calls = []
  const phases = []
  const logs = []
  const harnessErrors = []
  const waiting = []
  let inFlight = 0
  let maxInFlight = 0
  let spent = 0
  let clock = 0

  // A monotonic counter, not a wall clock: it orders dispatches so a test can assert that
  // one agent finished before another started, without any timing flakiness.
  function tick() {
    clock += 1
    return clock
  }

  async function acquire() {
    if (inFlight >= runtimeCap) {
      await new Promise((resolve) => waiting.push(resolve))
    }
    inFlight += 1
    if (inFlight > maxInFlight) maxInFlight = inFlight
  }

  function release() {
    inFlight -= 1
    const next = waiting.shift()
    if (next) next()
  }

  const exactKeys = Object.keys(responders).filter((k) => !k.endsWith('*'))
  const prefixKeys = Object.keys(responders)
    .filter((k) => k.endsWith('*'))
    .sort((a, b) => b.length - a.length)

  function resolveResponder(label) {
    if (exactKeys.includes(label)) return responders[label]
    for (const key of prefixKeys) {
      if (label.startsWith(key.slice(0, -1))) return responders[key]
    }
    return undefined
  }

  async function agent(prompt, opts = {}) {
    const label = opts.label || '(unlabelled)'
    const call = {
      label,
      phase: opts.phase,
      model: opts.model,
      agentType: opts.agentType,
      schema: opts.schema,
      prompt,
      startedAt: 0,
      endedAt: 0,
    }
    calls.push(call)
    if (budgetTotal !== null && spent >= budgetTotal) {
      throw new Error(`token budget exhausted: spent ${spent} of ${budgetTotal} (label ${label})`)
    }
    spent += tokensPerAgent
    await acquire()
    call.startedAt = tick()
    try {
      await new Promise((resolve) => setTimeout(resolve, tickMs))
      const responder = resolveResponder(label)
      if (responder === undefined) {
        throw new Error(`no responder registered for agent label "${label}"`)
      }
      const value = typeof responder === 'function' ? await responder(call, calls) : responder
      if (value !== null && opts.schema) {
        const problems = checkSchema(value, opts.schema)
        if (problems.length > 0) {
          throw new Error(`responder for "${label}" violates its schema: ${problems.join('; ')}`)
        }
      }
      return value
    } finally {
      call.endedAt = tick()
      release()
    }
  }

  // Contract: a thunk that throws (or whose agent errors) resolves to null in the result
  // array and the call itself never rejects. The harness still records the error so a
  // missing responder fails the suite loudly instead of being swallowed as a null.
  async function parallel(thunks) {
    return Promise.all(thunks.map(async (thunk) => {
      try {
        return await thunk()
      } catch (error) {
        harnessErrors.push({ where: 'parallel thunk', message: String(error && error.message) })
        return null
      }
    }))
  }

  // Contract: every item flows through every stage independently, items are processed
  // concurrently, there is no barrier between stages, and every stage callback receives
  // (prevResult, originalItem, index) with prevResult equal to the item for the first
  // stage. A stage that throws drops that item to null and skips its remaining stages.
  async function pipeline(items, ...stages) {
    return Promise.all(
      items.map(async (item, index) => {
        let previous = item
        for (const stage of stages) {
          try {
            previous = await stage(previous, item, index)
          } catch (error) {
            harnessErrors.push({ where: `pipeline stage on item ${index}`, message: String(error && error.message) })
            return null
          }
        }
        return previous
      }),
    )
  }

  function phase(title) {
    phases.push(title)
  }

  function log(message) {
    logs.push(message)
  }

  const budget = {
    total: budgetTotal,
    spent: () => spent,
    remaining: () => (budgetTotal === null ? Infinity : Math.max(0, budgetTotal - spent)),
  }

  function workflow() {
    throw new Error('workflow() nesting is not used by the workflows under test')
  }

  return {
    agent,
    parallel,
    pipeline,
    phase,
    log,
    budget,
    workflow,
    records: () => ({ calls, phases, logs, maxInFlight, harnessErrors }),
  }
}

/** Load, run and record one workflow invocation. */
export async function runWorkflow({
  source, args, responders, runtimeCap = 16, tickMs = 0, budgetTotal = null, tokensPerAgent = 1000,
}) {
  const harness = makeHarness({ responders, runtimeCap, tickMs, budgetTotal, tokensPerAgent })
  const fn = loadWorkflow(source)
  const result = await fn(
    harness.agent,
    harness.parallel,
    harness.pipeline,
    harness.phase,
    harness.log,
    args,
    harness.budget,
    harness.workflow,
  )
  return { result, ...harness.records() }
}
