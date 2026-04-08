$(document).ready(function () {
    $('.money').mask('#,##0', {
        reverse: true
    });

    $('#form-collaborator').append('<input hidden name="type_of" id="id_type_of">')
    var file_segment_orig = $('#file-segment').children();
    var table_detail = $('#table_detail').DataTable({
        info: false,
        processing: true,
        language: {
            url: '/ajax/datatable_spanish'
        },
        ajax: {
            url: '/partners/collaborators?type=active',
            dataSrc: "data"
        },
        columns: [{
                'data': 'id_document'
            },
            {
                'data': 'full_name'
            },
            {
                'data': 'last_contract.position_name'
            },
            {
                'data': 'last_contract.type_of_contract'
            },
            {
                'data': 'last_contract.initial_date',
                render: DataTable.render.moment('YYYY-MM-DD', 'YYYY/MM/DD')
            },
            {
                'data': 'last_contract.end_date',
                render: DataTable.render.moment('YYYY-MM-DD', 'YYYY/MM/DD')
            },
            {
                'data': 'last_contract.salary',
                render: $.fn.dataTable.render.number(',', '.', 0)
            },
        ],
        columnDefs: [{
                targets: [0, 2, 3, 4, 5, 6],
                className: 'center aligned'
            },
            {
                targets: 5,
                type: 'date-uk'
            }
        ],
        order: [
            [5, 'desc']
        ],
        fnRowCallback: function (nRow, aData, iDisplayIndex, iDisplayIndexFull) {
            if (aData.status == "Retirado") {
                $('td', nRow).addClass('error')
            }
        }
    })
    $('#table_detail tbody').on('click', 'tr', function () {
        let row = table_detail.row(this).data()
        $('#id_type_of').val('modify')
        $('#file-segment').empty();
        $('#div_table_contracts').remove()

        $('#submit-id-sbmt').val('Modificar')
        $('#modalCollaborator').find('.header').first().text('Datos: ' + row.first_name + ' ' + row.last_name)
        loadinfocollab(row)
        if (row.status == 'Retirado') {
            $('#submit-id-sbmt').addClass('disabled')
        } else {
            $('#submit-id-sbmt').removeClass('disabled')
        }

    })
    $('#table_detail tbody').on('contextmenu', 'tr', function (e) {
        table_detail.$('tr.active').removeClass('active');
        $(this).addClass('active')
        let row = table_detail.row(this).data()
        if (row.status == 'Activo') {
            $('#reactivate-collab').addClass('disabled')
            $('#retire-collab').removeClass('disabled')
            $('#new-salary').removeClass('disabled')
        } else {
            $('#reactivate-collab').removeClass('disabled')
            $('#retire-collab').addClass('disabled')
            $('#new-salary').addClass('disabled')
        }
        side = 'left'
        position = 'bottom'
        side_to_remove = 'right'
        position_to_remove = 'top'

        var width = window.innerWidth
        var height = window.innerHeight
        let popup_h = $('#popup-collab').height()
        let popup_w = $('#popup-collab').width()
        let computed_X_pos = e.pageX + popup_w + 30
        let computed_Y_pos = e.pageY + popup_h + 50
        console.log(height,computed_Y_pos)
        var positionX = e.pageX - 20
        let positionY = e.pageY
        if (computed_X_pos >= width) {
            positionX -= popup_w - 40
            side = 'right'
            side_to_remove = 'left'
        }
        if (computed_Y_pos >= height ) {
            positionY -= popup_h + 30
            position = 'top'
            position_to_remove = 'bottom'
        }
        positionY += 20
        $('#popup-collab').css({
                'left': positionX + 'px',
                'top': positionY + 'px',
            }).addClass('transition visible')
            .removeClass(side_to_remove)
            .removeClass(position_to_remove)
            .addClass(side)
            .addClass(position)
        return false;
    })
    $("#popup-collab").click(function (e) {
        let row = table_detail.row($('#table_detail tr.active')).data()
        switch (e.target.id) {
            case "retire-collab":
                $('#modalRetireCollab').modal('show')
                $('#calendar_end_date').calendar({
                    type: 'date',
                    text: calendar_spanish()
                })
                break;

            case "reactivate-collab":
                $('#id_duration_react').prop('disabled', false)
                $('#modalReactCollab').modal('show')
                $('#div_id_initial_date_react').calendar({
                    type: 'date',
                    text: calendar_spanish()
                })
                break;
            case "docs-collab":
                $('#id_collab_doc_id').val(row.id_document)
                $('#modalCollabDocs').modal('show')
                    .find('div.header').text('Cargar documentos a ' + row.full_name)
                break;
            case "view-docs-collab":
                $('#modalviewCollabDocs').modal('show')


                break;
        }
    })
    $('#modalviewCollabDocs').modal({
        onShow: function () {
            $('#table-docs tbody').empty()
            let row = table_detail.row($('#table_detail tr.active')).data()
            $('#collab-id-docs').val(row.id_document)
            $('#modalviewCollabDocs').find('div.header').text('Ver documentos de ' + row.full_name)
            $.ajax({
                url: '/partners/collaborators/uploadfiles',
                type: 'GET',
                data: {
                    'collab_doc': row.id_document
                },
                success: (xhr) => {
                    let info = xhr.data
                    for (i in info) {
                        data = info[i]
                        $('#table-docs tbody').append(
                            `<tr class="center aligned">
                                <td>${data.load_date}</td>
                                <td>${data.description}</td>
                                <td>
                                    <a target="_blank" href="/media/${data.file}"><i class="eye outline icon"></i></a>
                                    <a href="#" onclick="delete_doc(this);"><i class="red close icon"></i></a>
                                </td>
                            </tr>`
                        )
                    }
                }
            })
        }
    })
    $('#btn-new-collaborator').click(function () {
        $('#modalCollaborator').find('.header')
            .first().text('Nuevo Colaborador')
        $('#id_col_document').prop('readonly', false)
        $('#id_duration').prop('disabled', false)
        $('#submit-id-sbmt').removeClass('disabled')
        $('#div_table_contracts').remove()
        $('#file-segment').empty();
        $('#file-segment').append(
            file_segment_orig
        )
        $('#modalCollaborator').modal('show')
        $('.ui.calendar').calendar({
            type: 'date',
            text: calendar_spanish()
        })
        $('#form-collaborator').trigger('reset')
        $('#form-collaborator .ui.dropdown').dropdown('restore default text')
            .removeClass('loading')
        $('#submit-id-sbmt').val('Registrar')
        $('#id_type_of').val('create')

    })
    $('#form-collaborator').submit(function () {
        $(this).addClass('loading')
        $('#modalCollaborator .approve.button').addClass('disabled')

    });
    $('#form-retire').on('submit', function (e) {
        e.preventDefault();
        $(this).addClass('loading')
        let row = table_detail.row($('#table_detail tr.active')).data()
        let data = new FormData(this)
        data.append('action', 'retire')
        data.append('colab_document', row.id_document)
        $.ajax({
            type: 'POST',
            url: '/partners/collaborators',
            data: data,
            contentType: false,
            processData: false,
            success: (xhr) => {
                $('body').toast({
                    message: xhr.msj,
                    class: xhr.class,
                    showProgress: 'bottom',
                    displayTime: 'auto',
                });
                table_detail.ajax.reload()
                $('#modalRetireCollab').modal('hide')
                $('#form-retire').trigger('reset')
            },
            error: (xhr) => {
                $('body').toast({
                    message: 'Ha ocurrido un error, por favor contactate con el administrador del sistema',
                    class: 'error',
                    showProgress: 'bottom',
                    displayTime: 'auto',
                });
                console.log(xhr.responseText)
            },
            complete: () => {
                $('#form-retire').removeClass('loading')
            }
        })
    })
    $('#form-reactivate').on('submit', function (e) {
        e.preventDefault();
        $(this).addClass('loading')
        let row = table_detail.row($('#table_detail tr.active')).data()
        let data = new FormData(this)
        data.append('action', 'reactivate')
        data.append('colab_document', row.id_document)
        $.ajax({
            type: 'POST',
            url: '/partners/collaborators',
            data: data,
            contentType: false,
            processData: false,
            success: (xhr) => {
                $('body').toast({
                    message: xhr.msj,
                    class: xhr.class,
                    showProgress: 'bottom',
                    displayTime: 'auto',
                });
                table_detail.ajax.reload()
                $('#modalReactCollab').modal('hide')
                $('#form-reactivate').trigger('reset')
            },
            error: (xhr) => {
                $('body').toast({
                    message: 'Ha ocurrido un error, por favor contactate con el adminstrador del sistema',
                    class: 'error',
                    showProgress: 'bottom',
                    displayTime: 'auto',
                });
                console.log(xhr.responseText)
            },
            complete: () => {
                $('#form-reactivate').removeClass('loading')
            }
        })
    })
    $('#id_type_of_contract_react').on('change', function () {
        let value = $(this).val()
        if (value == 'Indefinido') {
            $('#id_duration_react').prop('disabled', true)
        } else {
            $('#id_duration_react').prop('disabled', false)
        }
    })
    $('#id_type_of_contract').on('change', function () {
        let value = $(this).val()
        if (value == 'Indefinido') {
            $('#id_duration').prop('disabled', true)
        } else {
            $('#id_duration').prop('disabled', false)
        }
    })
    $('.ui.dropdown').dropdown();
    $('.ui.checkbox').checkbox({
        onChecked: function () {
            table_detail.ajax.url('/partners/collaborators?type=all').load()
        },
        onUnchecked: function () {
            table_detail.ajax.url('/partners/collaborators?type=active').load()
        }
    })
    $('#form-collaborator').on('submit', function () {
        $('body').toast({
            class: 'info',
            message: 'Estamos procesando tu solicitud <i class="asterisk loading icon"></i>'
        })
    })
    loadcountries();

    function loadinfocollab(row_data) {
        $('#id_col_document').val(row_data.id_document)
            .prop('readonly', true)
        $('#id_col_first_name').val(row_data.first_name)
        $('#id_col_last_name').val(row_data.last_name)
        $('#id_col_phone').val(row_data.phone)
        $('#id_col_email').val(row_data.email)
        $('#id_bank_account_number').val(row_data.bank_account_number)
        $('#id_scholarity').parent('div.ui.dropdown')
            .dropdown('set selected', row_data.scholarity)

        $('#id_type_of_contract').parent('div.ui.dropdown')
            .dropdown('set selected', row_data.last_contract.type_of_contract)

        if (row_data.last_contract.type_of_contract == "Indefinido") {
            $('#id_duration').prop('disabled', true)
        } else {
            $('#id_duration').prop('disabled', false)
        }

        $('#id_bank_entity').parent('div.ui.dropdown')
            .dropdown('set selected', row_data.bank_entity.id)

        $('#id_account_type').parent('div.ui.dropdown')
            .dropdown('set selected', row_data.account_type)

        $('#id_eps').parent('div.ui.dropdown')
            .dropdown('set selected', row_data.eps)
        $('#id_pension').parent('div.ui.dropdown')
            .dropdown('set selected', row_data.pension)
        $('#id_cesantias').parent('div.ui.dropdown')
            .dropdown('set selected', row_data.cesantias)

        $('#id_position_name').val(row_data.last_contract.position_name)
        $('#id_duration').val(row_data.last_contract.duration)
        $('#id_salary').val(
            new Intl.NumberFormat('en-EN').format(row_data.last_contract.salary)
        )

        loadfullcountryinfo(row_data.country, row_data.state, row_data.city)

        $('#modalCollaborator').modal('show')
        $('#div_id_col_birth_date').calendar({
                type: 'date',
                text: calendar_spanish()
            })
            .calendar('set date', row_data.birth_date)
        $('#div_id_initial_date').calendar({
                type: 'date',
                text: calendar_spanish()
            })
            .calendar('set date', row_data.last_contract.initial_date)
        $('#id_col_address').val(row_data.address)


        let detail_contacts = ''
        for (i in row_data.all_contracts) {
            item = row_data.all_contracts[i]
            detail_contacts += `<tr>
            <td>${item.position_name}</td>
            <td class="center aligned">${item.type_of_contract}</td>
            <td class="center aligned">${item.initial_date}</td>
            <td class="center aligned">${item.end_date}</td>
            <td class="right aligned">$ ${new Intl.NumberFormat('en-EN').format(item.salary)}</td>
            </tr>`
        }


        let table_contracts = `
        <div id="div_table_contracts">
        <h4 class="ui center aligned header">Lista de contratos</h4>'
        <table class="ui small table">
            <thead>
            <tr class="center aligned">
                <th>Cargo</th>
                <th>Tipo contrato</th>
                <th>Fecha inicio</th>
                <th>Fecha fin</th>
                <th>Salario</th>            
            </tr>
            </thead>
            <tbody>
                ${detail_contacts}
            </tbody>
        </table></div>
        `
        $('#div-contract').append(table_contracts)

    }
})

function delete_doc(a) {
    let row = $(a).parents('tr')
    $('body').modal({
        title: 'Confirmar',
        class: 'basic tiny',
        closeIcon: true,
        content: '¿Estas seguro que deseas eliminar este documento?',
        actions: [{
                text: 'Si',
                class: 'ok green'
            },
            {
                text: 'No',
                class: 'cancel red'
            }
        ],
        onApprove: function () {
            $('.button.ok.green').addClass('loading')
            $.ajax({
                type: 'POST',
                url: '/partners/collaborators/uploadfiles',
                data: {
                    'csrfmiddlewaretoken': getCookie('csrftoken'),
                    'todo': 'delete',
                    'description': row[0].cells[1].innerText,
                    'collab': $('#collab-id-docs').val()
                },
                success: (xhr) => {
                    $(row).remove()
                    $('body').toast({
                        message: xhr.msj,
                        class: xhr.class,
                        showProgress: 'bottom',
                        displayTime: 'auto',
                    });
                },
                error: (xhr) => {
                    if (xhr.status == 403) {
                        $('body').toast({
                            message: 'No tienes permisos para realizar esto',
                            class: 'error',
                            showProgress: 'bottom',
                            displayTime: 'auto',
                        });
                    } else {
                        $('body').toast({
                            message: 'Ocurrió un error, por favor notifica al administrador del sistema',
                            class: 'error',
                            showProgress: 'bottom',
                            displayTime: 'auto',
                        });
                        console.log(xhr.responseText)
                    }
                },
                complete: (xhr) => {
                    $('.button.ok.green').removeClass('loading')
                }
            })
            return false;
        }
    }).modal('show');

}

function loadfullcountryinfo(country, state, city) {

    $('#id_country').parent('div.ui.dropdown')
        .dropdown('set selected', country)
    $('#id_state').parent('div.ui.dropdown').addClass('loading')
    $('#id_city').parent('div.ui.dropdown').addClass('loading')
    setTimeout(
        () => {
            $('#id_state').parent('div.ui.dropdown')
                .dropdown('set selected', state)
                .removeClass('loading')
        }, 1000
    )
    setTimeout(
        () => {
            $('#id_city').parent('div.ui.dropdown')
                .dropdown('set selected', city)
                .removeClass('loading')
        }, 2000
    )



    /*  $('#id_state').empty()
     $('#id_city').empty()
     $.ajax({
         type: 'get',
         url: '/ajax/getdatacountries',
         data: {
             'tipo': 'states',
             'pais': country
         },
         success: function (response) {
             var estados = response['estados']
             $('#id_state').append(
                 `<option value="">Selecciona...</option>`
             )
             for (estado in estados) {
                 $('#id_state').append(
                     `<option value=${estados[estado][0]}>${estados[estado][1]}</option>`
                 )
             }
             $.ajax({
                 type: 'get',
                 url: '/ajax/getdatacountries',
                 data: {
                     'tipo': 'cities',
                     'estado': state
                 },
                 success: function (response) {
                     var ciudades = response['ciudades']
                     $('#id_city').append(
                         `<option value="">Selecciona...</option>`
                     )
                     for (ciudad in ciudades) {
                         $('#id_city').append(
                             `<option value=${ciudades[ciudad][0]}>${ciudades[ciudad][1]}</option>`
                         )
                     }
                     $('#id_city').parent('div.ui.dropdown')
                     .dropdown('set selected',city)
                     $('#id_state').parent('div.ui.dropdown')
                     .dropdown('set selected',state)
                     $('#id_country').parent('div.ui.dropdown')
                     .dropdown('set selected',country)
                     
                 }
             })
         }
     }) */

}

function loadcountries() {
    $.ajax({
        type: 'get',
        url: '/ajax/getdatacountries',
        data: {
            'tipo': 'countries',
        },
        success: function (response) {
            var paises = response['paises']
            for (pais in paises) {
                $('#id_country').append(
                    `<option value=${paises[pais][0]}>${paises[pais][1]}</option>`
                )
            }
        }
    })
    $('#id_country').on('change', function () {
        let pais = $(this).val()
        $('#id_state').empty()
        $.ajax({
            type: 'get',
            url: '/ajax/getdatacountries',
            data: {
                'tipo': 'states',
                'pais': pais
            },
            success: function (response) {
                var estados = response['estados']
                $('#id_state').append(
                    `<option value="">Selecciona...</option>`
                )
                for (estado in estados) {
                    $('#id_state').append(
                        `<option value=${estados[estado][0]}>${estados[estado][1]}</option>`
                    )
                }
            }
        })
    })
    $('#id_state').on('change', function () {
        let estado = $(this).val()
        $('#id_city').empty()
        $.ajax({
            type: 'get',
            url: '/ajax/getdatacountries',
            data: {
                'tipo': 'cities',
                'estado': estado
            },
            success: function (response) {
                var ciudades = response['ciudades']
                $('#id_city').append(
                    `<option value="">Selecciona...</option>`
                )
                for (ciudad in ciudades) {
                    $('#id_city').append(
                        `<option value=${ciudades[ciudad][0]}>${ciudades[ciudad][1]}</option>`
                    )
                }
            }
        })
    })
}