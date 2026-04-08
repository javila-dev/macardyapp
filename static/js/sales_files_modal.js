$(document).ready(function () {
    // Abrir el modal y cargar los archivos
    function openSalesFilesModal(contractNumber, project) {
        $('#contract-number').val(contractNumber);
        $('#project').val(project);
        $('#sales-files-modal').modal('show');
        loadFiles(contractNumber, project);
    }

    // Cargar archivos asociados al contrato
    function loadFiles(contractNumber, project) {
        $.ajax({
            url: `/sales/${project}/files/${contractNumber}/get/`,
            type: 'GET',
            success: function (response) {
                if (response.status === 'success') {
                    const filesList = $('#files-list');
                    filesList.empty();
                    response.files.forEach(file => {
                        filesList.append(`
                            <div id="file-${file.id}" class="ui mini card">
                                <div class="content">
                                    <div class="header">${file.description}</div>
                                    <div class="meta">Tipo: ${file.file_type || 'N/A'}</div>
                                    <div class="description">
                                        <p>Observaciones: ${file.observations || 'N/A'}</p>
                                        <p>Cargado por: ${file.uploaded_by} el ${file.upload_date}</p>
                                    </div>
                                </div>
                                <div class="extra center aligned content">
                                    <a href="${file.file_url}" target="_blank" class="ui tiny button">Ver archivo</a>
                                    <button class="ui red tiny button delete-file-btn" data-file-id="${file.id}">Eliminar</button>
                                </div>
                            </div>
                        `);
                    });
                } else {
                    alert('Error al cargar los archivos.');
                }
            },
            error: function (xhr) {
                if (xhr.status === 404) {
                    alert('No se encontró la venta con ese contrato en este proyecto.');
                } else {
                    alert('Error al cargar los archivos.');
                }
            }
        });
    }

    // Manejar el envío del formulario para agregar un archivo
    $('#add-file-form').on('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(this);
        const contractNumber = $('#contract-number').val();
        const project = $('#project').val();
        const form = $(this);
        form.addClass('loading');
        $.ajax({
            url: `/sales/${project}/files/${contractNumber}/add/`,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function (response) {
                if (response.status === 'success') {
                    alert(response.message);
                    loadFiles(contractNumber, project);
                    $('#add-file-form')[0].reset();
                } else {
                    alert('Error al subir el archivo.');
                }
            },
            error: function () {
                alert('Error al subir el archivo.');
            },
            complete: function () {
                form.removeClass('loading');
            }
        });
    });

    // Manejar la eliminación de un archivo
    $(document).on('click', '.delete-file-btn', function () {
        const fileId = $(this).data('file-id');
        const contractNumber = $('#contract-number').val();
        const project = $('#project').val();

        $.ajax({
            url: `/sales/${project}/files/${fileId}/delete/`,
            type: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            success: function (response) {
                if (response.status === 'success') {
                    alert(response.message);
                    $(`#file-${fileId}`).remove();
                } else {
                    alert('Error al eliminar el archivo.');
                }
            },
            error: function () {
                alert('Error al eliminar el archivo.');
            }
        });
    });

    // Filtrar archivos por búsqueda
    $('#search-files').on('keydown', function () {
        const searchTerm = $(this).val().toLowerCase();
        $('.card').each(function () {
            const description = $(this).find('.header').text().toLowerCase();
            const fileType = $(this).find('.meta').text().toLowerCase();
            const observations = $(this).find('.description p:first').text().toLowerCase();

            if (description.includes(searchTerm) || fileType.includes(searchTerm) || observations.includes(searchTerm)) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });

    window.openSalesFilesModal = openSalesFilesModal;
});