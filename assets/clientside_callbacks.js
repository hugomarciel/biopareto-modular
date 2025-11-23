if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.clientside = {
    
    // 1. Función para Ocultar el Panel Automáticamente
    panel_auto_hide: function(panel_id, timeout_ms) {
        const panel = document.getElementById(panel_id);
        
        if (!panel) {
            return window.dash_clientside.no_update;
        }

        // Variable global en el scope de window para persistencia
        if (!window.panelHideTimer) {
            window.panelHideTimer = null;
        }

        // Al entrar el mouse: CANCELAR ocultamiento
        panel.onmouseenter = () => {
            if (window.panelHideTimer) {
                clearTimeout(window.panelHideTimer);
                window.panelHideTimer = null;
            }
        };

        // Al salir el mouse: INICIAR conteo
        panel.onmouseleave = () => {
            if (window.panelHideTimer) {
                clearTimeout(window.panelHideTimer);
            }
            
            window.panelHideTimer = setTimeout(() => {
                // Dash 2.9+: Usamos set_props para actualizar el store
                dash_clientside.set_props("ui-state-store", {data: {panel_visible: false}});
            }, timeout_ms);
        };

        return window.dash_clientside.no_update;
    },

    // 2. Función para Scroll Arriba
    scroll_to_top: function(n_clicks) {
        if (n_clicks) {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        return window.dash_clientside.no_update;
    }
};