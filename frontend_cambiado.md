# Cambios Frontend (form_frontend-2) — Rama 95 vs Main

## Resumen general
- **47 archivos** modificados | **2540 inserciones** | **1399 eliminaciones**
- Funcionalidades principales: repetir preguntas de feedback, revisión de respuestas, menú móvil unificado estilo onoratoai.com, refactorización completa del mobile UX

---

## Archivos nuevos

| Archivo | Descripción |
|---------|-------------|
| `src/pages/onoratoFarm/components/MobileChatActions.jsx` | Barra inferior de acciones móvil (back, report, listening indicator) |
| `src/pages/onoratoFarm/hooks/useRepeatQuestionFlow.js` | Hook custom para el flujo de repetir preguntas |
| `src/pages/onoratoFarm/utils/completedSessionStorage.js` | Utilidad localStorage para sesiones completadas |
| `src/pages/onoratoFarm/utils/feedbackItems.js` | Utilidad para construir items de milestone/feedback |
| `src/pages/onoratoFarm/utils/repeatQuestionStorage.js` | Utilidad localStorage para tracking de preguntas repetidas |

## Archivos eliminados

| Archivo | Razón |
|---------|-------|
| `src/components/panels/user_v2_mobile.jsx` | Nunca se importaba, código muerto |
| `src/pages/onoratoFarm/components/MobileMilestoneMenu.jsx` | Reemplazado por UserProfile con modo mobile |

---

## Archivos modificados

### Componentes principales

#### `src/components/panels/user.jsx`
- Añadido modo mobile (`isMobile` prop) con dropdown estilo onoratoai.com
- Acepta `milestoneMenu` prop para mostrar hitos de feedback
- Renderiza icono usuario/X como toggle, dropdown con milestones + idioma + logout
- Gestiona su propio estado open/close y click-outside

#### `src/pages/FormPage.jsx`
- Eliminado estado `isMobileMilestoneMenuOpen` y toda su lógica
- Eliminada función `renderMobileMilestoneStatusIcon` (~30 líneas)
- Simplificada `renderMobileCombinedMenu` — ahora solo renderiza `<UserProfile isMobile={true} />`
- Eliminada lógica duplicada de overlay backdrop para milestone menu

#### `src/pages/onoratoFarm/OnoratoFarm.jsx`
- Nuevo sistema de páginas con `MobileChatActions` para mobile
- Variables `showMobileChatActions` y `showMobileBackButton` para control de UI mobile
- `disableBackButton` incluye `currentPage === 5` (desactivar en pantalla final)
- Integración con `useRepeatQuestionFlow` hook
- Gestión de `milestoneMenu` prop pasado a subpáginas

#### `src/pages/onoratoFarm/components/HeaderOnoratoFarm.jsx`
- Reemplazado `MobileMilestoneMenu` por `UserProfile` con modo mobile
- Añadidos imports de `useNavigate` y `removeToken`
- Nueva variable `isReportDisabled` (solo `isSpeaking`) separada de `isDisabled` (back + speaking)
- El botón de report ya no se deshabilita cuando solo el back está disabled

#### `src/pages/onoratoFarm/FivePage.jsx` (Pantalla "Gracias por compartir")
- Eliminado hack `setIsSpeaking(true)` — ya no era necesario
- Añadido `disableBackButton={true}` al HeaderOnoratoFarm desktop
- Botón "¿Tuviste algún problema?" oculto en mobile (`{!isMobile && (...)}`)
- Eliminado prop `setIsSpeaking` de la firma del componente

#### `src/pages/onoratoFarm/SixthPage.jsx`
- Ajustes de layout para mobile

#### `src/pages/onoratoFarm/FourPage.jsx`
- Integración con flujo de repetir preguntas
- Mejoras de UX mobile

#### `src/pages/onoratoFarm/ThirdPage.jsx`
- Integración con flujo de repetir preguntas
- Mejoras de UX mobile

#### `src/pages/onoratoFarm/QuestionPage.jsx`
- Mejoras en el layout de revisión de preguntas/respuestas
- Adaptación mobile

#### `src/pages/onoratoFarm/SecondPage.jsx`
- Ajustes de layout

#### `src/pages/onoratoFarm/FirstPage.jsx`
- Nuevo prop `formProgress`
- Clases CSS refactorizadas (`firstpage-content-intro`, `firstpage-content-form`)

#### `src/pages/onoratoFarm/WaitingPage.jsx`
- Ajustes menores

#### `src/pages/FormComponent.jsx`
- Reducción de código (~56 líneas menos)

#### `src/pages/Login.jsx`
- Cambio menor

### API / Funciones

#### `functions/api_functions.js`
- Nueva función `getVoice(text, language)` — POST a `/onorato_farm/get_voice`
- Nueva función `parseBucketJsonArray(response)` — parsea respuesta JSON del bucket
- Nueva función `replaceFeedbackQuestion({...})` — POST a `/onorato_farm/feedback/replace`
- Nueva función `persistFeedbackAnswer({mode, version, question, response, context})` — wrapper que elige entre create/replace
- Nueva función `createTicket(message, subject)` — crea ticket de soporte

### Estilos CSS

#### `src/styles/UserProfile.css`
- Reescrito completamente: estilos desktop mantenidos + nuevos estilos mobile
- Nuevas clases `.user-profile-mobile-*` con estilo onoratoai.com
- Eliminados estilos legacy `.onorato-mobile`, `.onorato-half-user-trigger`, `.onorato-arrow-*`, `.onorato-user-expanded`, `.onorato-mobile-dropdown-menu`, `.onorato-mobile-menu-*`
- Dropdown mobile: `position: fixed`, full-width, border-radius 0, gradiente de fondo

#### `src/styles/FormPage.css`
- Eliminados ~250 líneas de estilos `.form-mobile-milestone-*` y `.mobile-profile-*`
- `.onorato_farm_container` en mobile: `border-radius: 0` (esquinas cuadradas)

#### `src/styles/onoratoFarm/General.css`
- Eliminados estilos `.mobile-milestone-*` y keyframe `mobileMilestoneDropdown`
- Footer mobile: padding reducido (`8px 16px`), botones min-height `44px` (era 56px)
- Eliminada animación `mobileMilestoneDropdown`

#### `src/styles/onoratoFarm/FivePage.css`
- Nuevo: botón "Revisar respuestas" en mobile con `width: 100%` y `white-space: nowrap`
- Nuevo: overrides para `.onorato_farm_container:has(.fivepage-content)`

#### `src/styles/onoratoFarm/SixthPage.css`
- Overrides para `.onorato_farm_container:has(.sixth-page-container)` en mobile

#### `src/styles/onoratoFarm/WaitingPage.css`
- `.waiting-page-content` en mobile: `border: none` (evita doble borde con padre), `width: 100%`

#### Otros CSS modificados:
- `src/styles/FormComponent.css` — 291+ líneas de mejoras responsive
- `src/styles/Responsive.css` — ajustes mobile
- `src/styles/onoratoFarm/FirstPage.css` — nuevas clases de contenido
- `src/styles/onoratoFarm/FourPage.css` — mejoras mobile
- `src/styles/onoratoFarm/QuestionPage.css` — ajustes de layout
- `src/styles/onoratoFarm/SecondPage.css` — mejoras mobile
- `src/styles/onoratoFarm/ThirdPage.css` — mejoras mobile
- `src/styles/onoratoFarm/LoadingScreen.css` — ajustes
- `src/styles/onoratoFarm/ArrowControls.css` — ajustes
- `src/styles/onoratoFarm/QuestionTooltip.css` — ajustes
- `src/styles/onoratoFarm/ReportComponent.css` — ajustes
- `src/styles/questionStyles/add_option.css` — ajustes
- `src/styles/questionStyles/base.css` — ajustes
- `src/styles/questionStyles/hour.css` — ajustes
- `src/styles/questionStyles/radio.css` — ajustes

### Traducciones

#### `src/locales/es/translation.json` y `src/locales/en/translation.json`
- Nuevas keys para flujo de repetir preguntas
- Nuevas keys para pantallas de feedback/milestones
- ~20 líneas cambiadas en cada archivo

---

## Funcionalidades añadidas

1. **Repetir preguntas de feedback** — el usuario puede repetir una pregunta específica del feedback y reemplazar su respuesta anterior
2. **Menú mobile unificado** — un solo componente `UserProfile` con modo mobile que reemplaza `MobileMilestoneMenu` y `user_v2_mobile`
3. **MobileChatActions** — barra inferior mobile con back/report/listening
4. **Revisión de respuestas** — pantalla para revisar las respuestas dadas durante el feedback
5. **Mejoras UX mobile** — esquinas cuadradas en contenedores, footer compacto, botones de acción más accesibles
