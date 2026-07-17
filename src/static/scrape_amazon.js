// 🔍 Ejecutar scraping Apify

let filasData = []; 

$('#btn-scrapear').click(function () {
      const selectedCountry = $('#pais').val();
        
        if (!selectedCountry) {
          Swal.fire("Error", "Por favor, seleccioná un país primero.", "error");
          return;
        }

        Swal.fire({
          title: 'Scrapeando...',
          text: 'Ejecutando búsqueda con Apify para: ' + selectedCountry,
          didOpen: () => Swal.showLoading()
        });

      localStorage.setItem('lugarSeleccionado', selectedCountry); // Guardar país en localStorage

       
      $.ajax({
          url: "/scrape_amazon/",
          method: "POST",
          contentType: "application/json",
          data: JSON.stringify({ sheet_name: selectedCountry }),


          success: function (response) {
                if (!response.success) {
                    Swal.fire("Error", response.error || "Algo salió mal", "error");
                    return;
                }
                debugger;
                localStorage.setItem("archivo_base", response.archivo_base);
                //---------------- TABLA A  (scraping) ----------------//
                const resultados = response.tablaA;
                let htmlA = `
                    <h3>Productos encontrados (Scraping Apify):</h3>
                    <table border="1" style="width:100%;border-collapse:collapse">
                    <thead>
                        <tr><th>Producto</th><th>Imagen</th><th>Título</th><th>Precio</th><th>Enlace</th></tr>
                    </thead><tbody>`;

                resultados.forEach((res, idx) => {
                    htmlA += `
                    <tr class="group-header" data-group="${idx}" style="cursor:pointer;background:#f0f0f0">
                        <td colspan="5"><strong>${res.producto}</strong> (${res.pais}) <span class="toggle-icon">▼</span></td>
                    </tr>`;

                    if (res.error) {
                    htmlA += `<tr class="group-${idx}" style="display:none"><td colspan="5" style="color:red;text-align:center">${res.error}</td></tr>`;
                    return;
                    }
                    res.items.forEach(item => {
                    htmlA += `
                        <tr class="group-${idx}" style="display:none">
                        <td></td>
                        <td><img src="${item.imagen}" width="80"></td>
                        <td>${item.titulo}</td>
                        <td>${item.precio} €</td>
                        <td><a href="${item.url}" target="_blank">Ver producto</a></td>
                        </tr>`;
                    });
                });
                htmlA += `</tbody></table>`;

                



                //---------------- Inyectar en el DOM ----------------//
                $('#resultado').html(htmlA );

                // toggle filas de la tabla A
                $('.group-header').on('click', function () {
                    const g = $(this).data('group');
                    $(`.group-${g}`).toggle();
                    const ic = $(this).find('.toggle-icon');
                    ic.text(ic.text() === '▼' ? '▲' : '▼');
                });

                Swal.fire("¡Listo!", "Scraping completado con éxito.", "success");
                },
                error() { Swal.fire("Error", "No se pudo contactar al backend.", "error"); }

      });
    });





















































$('#btn-scrapear-imagenes').click(function () {
       
        
         const selectedCountry =  localStorage.getItem('lugarSeleccionado'); // Guardar país en localStorage
         let archivoBase = localStorage.getItem("archivo_base");
       
         const selectedFile = $('#ArchivosCargados').val(); // 2. Tomamos el archivo
      
        if (!selectedCountry || !selectedFile) {
            Swal.fire("Error", "Por favor, seleccioná un país y un archivo primero.", "error");
            return;
        }

        
            Swal.fire({
                title: 'Scrapeando...',
                text: `Procesando archivo ${selectedFile} para ${selectedCountry}`,
                didOpen: () => Swal.showLoading()
            });


     $.ajax({
            url: "/scrape_amazon_dpia_scraping_imagenes/",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
            sheet_name: selectedCountry,
            nombre_archivo: selectedFile,
            archivo_base: archivoBase
          
            }),

          success: function (response) {
                if (!response.success) {
                    Swal.fire("Error", response.error || "Algo salió mal", "error");
                    return;
                }
                if (response.archivo_relacionado) {
                        localStorage.setItem("archivoRelacionado", response.archivo_relacionado);
                    }
                //---------------- TABLA A  (scraping) ----------------//
                const resultados = response.tablaA;
                let htmlA = `
                    <h3>Productos encontrados (Scraping Apify):</h3>
                    <table border="1" style="width:100%;border-collapse:collapse">
                    <thead>
                        <tr><th>Producto</th><th>Imagen</th><th>Título</th><th>Precio</th><th>Enlace</th></tr>
                    </thead><tbody>`;

                resultados.forEach((res, idx) => {
                    htmlA += `
                    <tr class="group-header" data-group="${idx}" style="cursor:pointer;background:#f0f0f0">
                        <td colspan="5"><strong>${res.producto}</strong> (${res.pais}) <span class="toggle-icon">▼</span></td>
                    </tr>`;

                    if (res.error) {
                    htmlA += `<tr class="group-${idx}" style="display:none"><td colspan="5" style="color:red;text-align:center">${res.error}</td></tr>`;
                    return;
                    }
                    res.items.forEach(item => {
                    htmlA += `
                        <tr class="group-${idx}" style="display:none">
                        <td></td>
                        <td><img src="${item.imagen}" width="80"></td>
                        <td>${item.titulo}</td>
                        <td>${item.precio} €</td>
                        <td><a href="${item.url}" target="_blank">Ver producto</a></td>
                        </tr>`;
                    });
                });
                htmlA += `</tbody></table>`;

                //---------------- TABLA B  (sheet + top-3) -----------//

                    filasData = response.tablaB;
                    let htmlB = `
                    <h3 style="margin-top:40px;">Selección final (Sheet + Top-3)</h3>
                    <table border="1" style="width:100%;border-collapse:collapse;">
                    <thead><tr>`;

                    // Cabecera dinámica
                    Object.keys(filasData[0]).forEach(col => {
                    htmlB += `<th>${col}</th>`;
                    });
                    htmlB += `<th>Acción</th></tr></thead><tbody>`;   // ← “Acción” aquí, todavía en thead

                    // Filas de datos
                    filasData.forEach((f, idx) => {
                    htmlB += "<tr>";
                    Object.keys(filasData[0]).forEach(col => {
                        const val = f[col] ?? "";
                        if (col.startsWith("imagen") || col === "item_imagen") {
                        htmlB += `<td>${val ? `<img src="${val}" width="60">` : ""}</td>`;
                        } else if (col.endsWith("_url") || col.startsWith("búsqueda_")) {
                        htmlB += `<td>${val ? `<a href="${val}" target="_blank">link</a>` : ""}</td>`;
                        } else {
                        htmlB += `<td>${val}</td>`;
                        }
                    });
                    // Botón individual con índice correcto
                    htmlB += `<td><button class="btn-enviar" data-idx="${idx}">Enviar</button></td>`;
                    htmlB += "</tr>";
                    });

                    htmlB += "</tbody></table>";



                //---------------- Inyectar en el DOM ----------------//
                $('#resultado').html(htmlA + htmlB);

                // toggle filas de la tabla A
                $('.group-header').on('click', function () {
                    const g = $(this).data('group');
                    $(`.group-${g}`).toggle();
                    const ic = $(this).find('.toggle-icon');
                    ic.text(ic.text() === '▼' ? '▲' : '▼');
                });

                Swal.fire("¡Listo!", "Scraping completado con éxito.", "success");
                },
                error() { Swal.fire("Error", "No se pudo contactar al backend.", "error"); }

      });
    });



