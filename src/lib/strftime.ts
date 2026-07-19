import type { NordlysPayload } from './types'

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export interface Formats {
  time: string
  date: string
  date_year: string
  datetime: string
  weekday_time: string
}

export const DEFAULT_FORMATS: Formats = {
  time: '%H:%M',
  date: '%d %b',
  date_year: '%d %b %Y',
  datetime: '%d %b %Y, %H:%M',
  weekday_time: '%a %H:%M',
}

export function formatsOf(payload: NordlysPayload): Formats {
  return { ...DEFAULT_FORMATS, ...(payload.config.formats ?? {}) }
}

/**
 * Format a unix-seconds timestamp with a small strftime subset
 * (`%H %M %S %d %m %b %a %Y %I %p %%`), month/day names in English.
 * Replaces every `toLocaleString` so formatting is config-driven, not
 * browser-locale-driven.
 */
export function strftime(ts: number, format: string): string {
  const d = new Date(ts * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return format.replace(/%([HMSdmbaYIp%])/g, (_match, code: string) => {
    switch (code) {
      case 'H':
        return pad(d.getHours())
      case 'M':
        return pad(d.getMinutes())
      case 'S':
        return pad(d.getSeconds())
      case 'd':
        return pad(d.getDate())
      case 'm':
        return pad(d.getMonth() + 1)
      case 'b':
        return MONTHS[d.getMonth()]
      case 'a':
        return DAYS[d.getDay()]
      case 'Y':
        return String(d.getFullYear())
      case 'I':
        return pad(((d.getHours() + 11) % 12) + 1)
      case 'p':
        return d.getHours() < 12 ? 'AM' : 'PM'
      case '%':
        return '%'
      default:
        return '%' + code
    }
  })
}
