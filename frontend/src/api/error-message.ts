/** Turn gateway failures into useful messages while retaining API validation details. */
export function apiErrorMessage(detail: unknown, status: number | undefined, fallback: string): string {
  if (detail == null && status === 502) {
    return 'The application server is unavailable. Please try again shortly.'
  }
  if (Array.isArray(detail)) {
    return detail.map(item => `${item?.loc?.slice(-1)[0] ?? 'Input'}: ${item?.msg ?? 'Invalid value'}`).join(' · ')
  }
  return String(detail ?? fallback)
}
