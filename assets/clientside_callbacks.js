if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.clientside = {
    
    // 1. LÓGICA MAESTRA DE VISIBILIDAD DEL PANEL
    panel_auto_hide: function(panel_id, timeout_ms, is_pinned) {
        const panel = document.getElementById(panel_id);
        
        if (!panel) {
            return window.dash_clientside.no_update;
        }

        // --- GESTIÓN DE VARIABLES GLOBALES (SINGLETONS) ---
        // Usamos window para asegurar persistencia entre llamadas del callback
        if (!window.panelState) {
            window.panelState = {
                timer: null,
                clickListenerAttached: false
            };
        }

        // Función auxiliar para cerrar el panel
        const closePanel = () => {
            // Solo cerramos si NO está fijado (pinned)
            // Obtenemos el valor actual del switch directamente del DOM por seguridad o confiamos en el argumento
            // Para consistencia con React/Dash, usaremos el argumento is_pinned, 
            // pero si la función se llama asíncronamente (timer), debemos tener cuidado.
            
            // Verificación final de seguridad:
            // Si el mouse está sobre el panel, NO cerramos (edge case del timer)
            if (panel.matches(':hover')) return;

            dash_clientside.set_props("ui-state-store", {data: {panel_visible: false}});
        };

        // --- A. GESTIÓN DEL CLICK FUERA (CLICK OUTSIDE) ---
        // Solo añadimos el listener una vez
        if (!window.panelState.clickListenerAttached) {
            document.addEventListener('click', function(event) {
                const panelRef = document.getElementById(panel_id);
                const toggleBtn = document.getElementById('floating-toggle-panel-btn');
                
                // Si el panel no existe o está oculto visualmente (right < 0), ignorar
                if (!panelRef || panelRef.style.right === '-450px') return;

                // Si el usuario clickeó DENTRO del panel o en el botón que lo abre, ignorar
                if (panelRef.contains(event.target) || (toggleBtn && toggleBtn.contains(event.target))) {
                    return;
                }

                // Si está FIJO (Pinned), ignorar clicks fuera
                // Nota: Leemos el estado del switch directamente del DOM para tener el valor "vivo"
                // ya que 'is_pinned' en el closure del evento podría ser viejo.
                const pinSwitch = document.getElementById('pin-interest-panel-switch');
                const isPinnedLive = pinSwitch ? pinSwitch.checked : false; // .checked para input type checkbox/switch de bootstrap

                if (isPinnedLive) return;

                // Si llegó aquí: Es click fuera Y no está fijo -> CERRAR
                dash_clientside.set_props("ui-state-store", {data: {panel_visible: false}});
            });
            window.panelState.clickListenerAttached = true;
        }

        // --- B. GESTIÓN DEL MOUSE LEAVE (TIMER 5s) ---
        
        // Limpiar timer previo si existe (reset)
        if (window.panelState.timer) {
            clearTimeout(window.panelState.timer);
            window.panelState.timer = null;
        }

        // Al entrar el mouse: Cancelar cualquier cierre pendiente
        panel.onmouseenter = () => {
            if (window.panelState.timer) {
                clearTimeout(window.panelState.timer);
                window.panelState.timer = null;
            }
        };

        // Al salir el mouse: Iniciar conteo (SOLO SI NO ESTÁ PINNED)
        panel.onmouseleave = () => {
            if (is_pinned) return; // Si está fijo, no hacemos nada al salir

            // Iniciar timer
            window.panelState.timer = setTimeout(() => {
                closePanel();
            }, timeout_ms);
        };

        return window.dash_clientside.no_update;
    },

    // 2. Función para Scroll Arriba (Sin cambios)
    scroll_to_top: function(n_clicks) {
        if (n_clicks) {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        return window.dash_clientside.no_update;
    }
};