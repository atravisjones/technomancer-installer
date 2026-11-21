// The topics a chat can be colored by. Setup replaces this file with the
// person's own list; this one is the default for a mod loaded straight from the repo.
export const TOPICS = [
  {
    id: 'company',
    label: 'Work',
    color: '#c4552e',
    hue: 16,
    dot: '\u{1F7E0}',
    words: ['work', 'business', 'company', 'lead', 'leads', 'job', 'jobs', 'customer', 'customers', 'estimate', 'crew'],
  },
  {
    id: 'personal',
    label: 'Personal',
    color: '#3f9d5a',
    hue: 140,
    dot: '\u{1F7E2}',
    words: ['personal', 'family', 'fitness', 'budget', 'taxes'],
  },
  {
    id: 'assistant',
    label: 'Assistant',
    color: '#2f86c9',
    hue: 206,
    dot: '\u{1F535}',
    words: ['claude', 'skill', 'skills', 'mod', 'mods', 'memory', 'tint', 'setup', 'settings'],
  },
]
