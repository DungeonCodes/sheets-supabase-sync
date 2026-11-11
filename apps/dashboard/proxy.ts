import { NextRequest, NextResponse } from 'next/server';
import { hasAccess } from './lib/auth';

export function proxy(request: NextRequest) {
  const required = process.env.DASHBOARD_ACCESS_TOKEN;
  if (!required && process.env.DASHBOARD_MODE !== 'postgres') return NextResponse.next();
  if (!required || required.length < 24) return new NextResponse('Configuração de acesso indisponível', {status:503});
  if (!hasAccess(request.headers.get('authorization') ?? '',required)) return new NextResponse('Acesso necessário', {status:401,headers:{'WWW-Authenticate':'Basic realm="Dashboard local", charset="UTF-8"','Cache-Control':'no-store'}});
  return NextResponse.next();
}
export const config = { matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'] };
