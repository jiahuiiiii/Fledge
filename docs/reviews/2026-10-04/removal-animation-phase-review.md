# Removal notice animation — 4 October 2026

The user requested a smooth stock-removal notice: content below the header moves down, its green background reveals from left to right, and an undo icon sits beside close on the right. The notice now sits immediately after the persistent header. A 320ms grid-row transition opens/closes its natural height; a 360ms background sweep and short content fade accompany entry. Repeated removals refresh the message/sweep and Undo restores the latest removed company. The notice retains its message during exit without leaving hidden controls interactive.

Icon buttons have accessible names, hover titles and visible keyboard focus. Reduced-motion preferences disable transitions and the sweep. Desktop height is 52px; long text wraps naturally on phones while controls remain grouped. Sidebar removal continues to be browser-local visibility only, preserving research and monitoring.

Production build and complete frontend formatting pass. The existing read-only interaction journey passes custom menus, keyboard controls, removal/undo/reload/restore, empty-sidebars and phone behavior. Visual checks inspect 1440/390/320px screens, repeated removals, dismissal, keyboard activation and reduced motion. Captured frame measurements include 11 intermediate height frames, fractional left-to-right sweep values, a stationary header and equal 52px displacement of the demo strip and workspace. Desktop/phone screenshots were inspected. No new permanent tests were added for this presentation change; the temporary visual check is retained with evidence. The same visual/behavior check passes against the installed app on port 8841; installed screenshots and animation-frame measurements are retained in the evidence folder.

One agent reviewed five perspectives: product (requested feedback preserved); UX (smooth entry/exit and adjacent controls); engineering (local component, no dependencies); accessibility (named icons, inert collapsed controls, reduced motion); evidence/cost (read-only checks, no source/model calls). Browser checks cover Chrome, not complete cross-browser or participant validation.

No backend, schema or data changes; no API spend. Broader project gaps remain unchanged.

Evidence: `.local/live-tests/removal-animation-20261004T051942Z/`. Backup: `.local/backups/phase66-removal-animation-20261004T051942Z/`.
