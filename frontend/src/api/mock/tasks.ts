/**
 * Mock implementation of gemsApi.
 *
 * Returns hardcoded UserTasks with a short delay to make spinners visible.
 * The run() function simulates SSE streaming via ReadableStream, matching
 * the real interface so GemRunner needs no special casing.
 */
import type { UserTask } from '../tasks'

const SAMPLE_TASKS: UserTask[] = [
  {
    id: 'summarise-text',
    name: 'Summarise Text',
    description: 'Condense any passage into a clear, concise summary.',
    hue: 'indigo',
    template: 'Summarise the following text in {{ language }}:\n\n{{ text }}',
    args: [
      { type: 'string', name: 'text', description: 'The text to summarise', default: '' },
      {
        type: 'choice',
        name: 'language',
        description: 'Output language',
        default: 'English',
        options: ['English', 'Italian', 'French', 'Spanish'],
      },
    ],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
    doc_folder_ids: [],
    doc_ids: [],
    tools: [],
  },
  {
    id: 'translate',
    name: 'Translate',
    description: 'Convert text from one language to another.',
    hue: 'emerald',
    template: 'Translate the following text into {{ target_language }}:\n\n{{ text }}',
    args: [
      { type: 'string', name: 'text', description: 'Text to translate', default: '' },
      {
        type: 'choice',
        name: 'target_language',
        description: 'Target language',
        default: 'Italian',
        options: ['Italian', 'French', 'Spanish', 'German', 'Portuguese'],
      },
    ],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
    doc_folder_ids: [],
    doc_ids: [],
    tools: [],
  },
  {
    id: 'draft-letter',
    name: 'Draft a Letter',
    description: 'Write a professional letter from key bullet points.',
    hue: 'amber',
    template: 'Write a professional letter about the following:\n\n{{ topic }}\n\nTone: {{ tone }}',
    args: [
      { type: 'string', name: 'topic', description: 'Main points to cover', default: '' },
      {
        type: 'choice',
        name: 'tone',
        description: 'Letter tone',
        default: 'Formal',
        options: ['Formal', 'Friendly', 'Apologetic', 'Assertive'],
      },
    ],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
    doc_folder_ids: [],
    doc_ids: [],
    tools: [],
  },
  {
    id: 'explain-simply',
    name: 'Explain Simply',
    description: 'Break down a complex topic for a beginner audience.',
    hue: 'rose',
    template: 'Explain "{{ topic }}" simply, as if speaking to a {{ audience }}.',
    args: [
      { type: 'string', name: 'topic', description: 'Topic to explain', default: '' },
      {
        type: 'choice',
        name: 'audience',
        description: 'Target audience',
        default: 'curious 12-year-old',
        options: ['curious 12-year-old', 'non-technical adult', 'complete beginner'],
      },
    ],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
    doc_folder_ids: [],
    doc_ids: [],
    tools: [],
  },
  {
    id: 'meeting-notes',
    name: 'Meeting Notes',
    description: 'Turn rough meeting notes into structured minutes.',
    hue: 'violet',
    template: 'Convert these rough meeting notes into structured minutes:\n\n{{ notes }}',
    args: [
      { type: 'string', name: 'notes', description: 'Rough notes from the meeting', default: '' },
    ],
    has_image: false,
    has_audio: false,
    output_mode: 'text',
    doc_folder_ids: [],
    doc_ids: [],
    tools: [],
  },
]

/** Simulated canned response text for the run mock. */
const CANNED_RESPONSE =
  'This is a simulated response from the mock API. ' +
  'It streams word by word to demonstrate the streaming UI. ' +
  'In production, tokens come from the local Ollama model. ' +
  'The output area updates in real time as each token arrives.'

function delay(ms: number): Promise<void> {
  return new Promise(r => setTimeout(r, ms))
}

export const gemsApi = {
  list: async (): Promise<UserTask[]> => {
    await delay(200)
    return [...SAMPLE_TASKS]
  },

  get: async (id: string): Promise<UserTask> => {
    await delay(150)
    const task = SAMPLE_TASKS.find(t => t.id === id)
    if (!task) throw new Error(`Gem not found: ${id}`)
    return { ...task }
  },

  create: async (task: UserTask): Promise<UserTask> => {
    await delay(300)
    return { ...task }
  },

  update: async (_id: string, task: UserTask): Promise<UserTask> => {
    await delay(300)
    return { ...task }
  },

  delete: async (_id: string): Promise<void> => {
    console.log(`Mock delete gem with id ${_id}`)
    await delay(200)
  },

  /**
   * Simulates SSE streaming by yielding words from a canned response one at a
   * time via ReadableStream. Matches the real Response interface so GemRunner
   * needs no special casing. Image and audio args are accepted but ignored.
   */
  run: (
    _id: string,
    _values: Record<string, string>,
    _image?: { blob: Blob; mime: string },
    _audio?: { blob: Blob; mime: string },
  ): Promise<Response> => {
    console.log(`Mock run gem with id ${_id} and values`, _values)
    const words = CANNED_RESPONSE.split(' ')
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      async start(controller) {
        await delay(400) // simulate model startup latency
        for (const word of words) {
          controller.enqueue(encoder.encode(`data: ${word} \n\n`))
          await delay(80)
        }
        controller.enqueue(encoder.encode('data: [DONE]\n\n'))
        controller.close()
      },
    })
    return Promise.resolve(
      new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    )
  },
}
