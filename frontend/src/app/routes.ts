// Application route definitions.
// This single-page agent application uses a lightweight route registry so
// navigation targets are centralised and easily extended (e.g. when adding
// dedicated pages). The shell renders the active route's component.
import type { ComponentType } from 'react'
import App from './App'

export interface RouteDefinition {
  path: string
  name: string
  component: ComponentType
}

export const routes: RouteDefinition[] = [
  {
    path: '/',
    name: 'Workspace',
    component: App,
  },
]

export function resolveRoute(pathname: string): RouteDefinition {
  return routes.find((r) => r.path === pathname) ?? routes[0]
}
