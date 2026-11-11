import { timingSafeEqual } from 'node:crypto';

export function hasAccess(header: string, expected: string): boolean {
  if (!header.startsWith('Basic ')) return false;
  const decoded=Buffer.from(header.slice(6),'base64').toString('utf8');
  if (!decoded.startsWith('dashboard:')) return false;
  const actual=Buffer.from(decoded.slice('dashboard:'.length)), required=Buffer.from(expected);
  return actual.length===required.length && timingSafeEqual(actual,required);
}
