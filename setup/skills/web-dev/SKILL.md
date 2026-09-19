---
name: web-dev
description: Desarrollo web: HTML, CSS, JS, React, Vue, Node y APIs REST.
---

# web-dev

Guia practica de desarrollo web moderno 2026. Objetivo: construir paginas web y
APIs con las practicas y APIs mas modernas (Baseline de navegadores), evitando
tecnicas viejas.

## HTML5 moderno

- Semantica correcta: un solo `main`, un `h1`, jerarquia sin saltos; usar
  `header`, `nav`, `section`, `article`, `aside`, `footer`, `search`.
- NO usar "div soup" ni tablas para layout.
- Accesibilidad: no usar ARIA si un elemento nativo ya lo hace. `lang="es"` en
  `<html>`, `alt` descriptivo (o `alt=""` si es decorativo), `aria-label` en
  iconos solos, `aria-live="polite"` en regiones dinamicas.
- Formularios: usar la Constraint Validation API del navegador (types `email`,
  `url`, `date`, `range`, etc.), `autocomplete`, `inputmode`, `pattern`,
  `:user-invalid` en CSS. Sin librerias de validacion necesarias.
- Atributos modernos: `loading="lazy"` y `decoding="async"` en img, `fetchpriority`
  en el hero, `<dialog>` para modales (showModal, returnValue, ::backdrop),
  Popover API (`popovertarget`, `popover="auto"`), `inert` para desactivar
  subarboles, `<details>/<summary>` para acordeones, `<template>` + cloneNode.
- Ejemplo clave: `<img src="foto.jpg" alt="Descripcion" loading="lazy" decoding="async">`.

## CSS moderno

- Grid para layout de 2 ejes, Flexbox para 1 eje. `gap` para separar (no margin).
- Grid auto-responsive sin media queries:
  `grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))`.
- Custom properties (variables) en `:root` + `light-dark()` para temas claro/oscuro.
- `@layer` para organizar (reset, base, componentes, utilidades) y acabar con las
  guerras de especificidad.
- Container queries (`container: panel / inline-size` + `@container`) y `subgrid`
  para componentes adaptables.
- Selectores modernos: `:has()` (padre condicionado por hijo), `aspect-ratio`,
  `clamp()` para tipografia fluida, `color-mix()` en lugar de SASS darken.
- Animaciones: View Transitions API (`document.startViewTransition`),
  scroll-driven animations, nesting nativo `&`, `@scope`.
- Organizar con `@layer` + custom properties + CSS Modules. NO SASS salvo equipos
  que ya lo usen. NO `!important`, NO floats, NO media queries por componente.
- Ejemplo layout: body { display: grid; grid-template-areas: "header header"
  "sidebar main" "footer footer"; }.

## JavaScript moderno (ES2024/2025)

- Siempre: optional chaining `?.` y nullish coalescing `??` (no `||` para defaults).
- Destructuring + rest + spread. Modulos ESM (`import`/`export`, `type="module"`).
- Metodos inmutables de array: `toSorted`, `toSpliced`, `toReversed`, `with`.
- async/await + fetch con `res.ok` y `AbortSignal.timeout`.
- Nuevos: `Promise.withResolvers`, `Promise.try`, `Array.fromAsync`,
  `Object.groupBy`, `structuredClone` (reemplaza JSON.parse(JSON.stringify())).
- DOM moderno: template + `replaceChildren`, delegacion de eventos con
  `e.target.closest()`. NO innerHTML+=, NO un listener por elemento.
- Web Components: Custom Elements + Shadow DOM (`customElements.define`).
  React 19 los soporta; Lit es la libreria de referencia.
- Web APIs utiles: IntersectionObserver (lazy render), ResizeObserver, Clipboard,
  Web Animations API, AbortController.
- Temporal (fechas) esta en Stage 3: usar `@js-temporal/polyfill` si se necesita.

## TypeScript 5.x

- tsconfig moderno: `strict: true`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`,
  `verbatimModuleSyntax`, `noEmit` (el bundler compila), `moduleResolution: "bundler"`.
- Tipos: unions, generics, utility types (`Omit`, `Pick`, `Partial`, `Record`),
  `satisfies`, `Awaited<ReturnType<...>>`.
- NO `any` como comodin, NO `@ts-ignore`.

## Frameworks frontend 2026 (elegir segun caso)

- Sitio estatico simple (blog, landing, docs): HTML+CSS+JS vanilla o Astro+Vite.
- App interactiva media (dashboard, CRUD): React 19 o Vue 3; Svelte 5 si priorizas
  tamaño y velocidad (runes: $state, $derived, $props).
- App compleja (grande, multi-equipo, SSR): React 19 + Next.js o Vue 3 + Nuxt,
  con TypeScript.
- Componentes reutilizables entre proyectos: Lit (Web Components).
- Prototipo minimo: vanilla JS + import map.
- NO frameworks muertos (Backbone, jQuery UI), NO CRA (deprecado).

## Herramientas de build

- Vite es el estandar moderno (dev server ESM + build con Rolldown, plantillas
  vanilla/react/vue/svelte/solid/lit). `npm create vite@latest mi-app -- --template react-ts`.
- NO configurar webpack a mano, NO Babel para lo que ya esta transformado.
- NO SASS salvo equipos que ya lo usen (CSS nativo cubre nesting y variables).

## Node.js backend moderno

- Node 24 LTS. Sin nodemon (usa `node --watch`), sin dotenv (usa `node --env-file=.env`),
  test runner nativo `node --test` para proyectos simples.
- Frameworks: Hono (TypeScript-first, edge/serverless, ~14kB) o Fastify (Node puro
  con esquemas JSON y pino) para APIs nuevas; Express solo para mantener apps existentes.
- API minima con Hono + Zod: `zValidator('json', schema)` valida el body.
- ORM: Drizzle (nuevo, SQL-first, serverless-ready) > Prisma (productividad, mas peso)
  > Kysely (solo queries tipadas).
- Validacion: zod v4 (`z.object`, `safeParse`, `z.infer`).
- Auth: sesiones en cookie (mejor-auth, heredero de Lucia que murio en 2025) para
  apps con UI; JWT (jose, no jsonwebtoken) para APIs stateless.
- WebSockets: `ws` para sockets crudos; Socket.IO para chat/rooms/reconexion.
- Tests: vitest + supertest (o node:test). Playwright para e2e.
- Despliegue: Docker (node:24-alpine) o serverless (Hono corre en Cloudflare Workers).

## Testing web (piramide)

- Unit: Vitest (v4, Browser Mode). Componente: Testing Library (queries por rol,
  no por clase CSS). E2E: Playwright (locators por rol, auto-wait, `npx playwright codegen`).
- NO Selenium, NO sleeps.

## Recursos

- MDN (developer.mozilla.org) es la referencia canonica de HTML/CSS/JS.
- Vite, React, Vue, Svelte, Playwright, Vitest tienen docs oficiales actualizadas.
- Verificar compatibilidad con caniuse.com o la tabla "Baseline" de MDN.
