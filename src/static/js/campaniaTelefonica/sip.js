async function llamarContacto(telefono, opciones) {
    const payload = {
        telefono: telefono,
        usuario_id: opciones && opciones.usuarioId ? opciones.usuarioId : null,
        campania_id: opciones && opciones.campaniaId ? opciones.campaniaId : null
    };

    try {
        const response = await fetch('/campaniaTelefonica/generarSipLink/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok || !data.success || !data.sip_link) {
            throw new Error(data.error || 'No fue posible generar el enlace SIP');
        }

        window.location.href = data.sip_link;
    } catch (error) {
        console.error('Error SIP:', error);
        window.alert(error.message || 'No fue posible iniciar la llamada SIP');
    }
}