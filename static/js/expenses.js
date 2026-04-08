
$(document).ready(function(){
    var tableexpenses = $('#table-expenses').DataTable({
        processing: true,
        language:{
            url:'/ajax/datatable_spanish'
        },
        ajax:{
            'url':'/finance/'+project+'/expenses'
        },
        columns:[
            {'data':'date',render:DataTable.render.moment( 'YYYY-MM-DD', 'YYYY/MM/DD')},
            {'data':'description'},
            {'data':'costcenter.name'},
            {'data':'value',
            'render': DataTable.render.number( ',', '.',0, '$' )},
            {'data':'user.username'},
        ],
        order:[[0,'desc']],
        columnDefs : [
            {targets:[0,2,4],className: 'center aligned'},
            {targets:[3],className: 'right aligned'},
            {targets:0,type:'date-uk'}
        ]
    })
    $('.money').mask('#,##0', {reverse: true});
    $('.ui.dropdown').dropdown();
    $('.ui.calendar').calendar({
        type: 'date',
        text: calendar_spanish(),
    })
    $('#btn-remove-search').click(function(){
        let url = `/finance/${project}/expenses`
        $('.ui.calendar').calendar('clear')
        tableexpenses.ajax.url(url).load()
    })
    $('#btn-search-by-date').click(function(){
        let initial_date = $('#date-from').val()
        let final_date = $('#date-to').val()
        if (initial_date == "" || final_date == '') {
            $('body')
                .toast({
                    class: 'error',
                    message: `Debes escoger una fecha inicial y una fecha final !`
                })
                ;
            return;
        }
        let url = `/finance/${project}/expenses?from_date=${initial_date}&to_date=${final_date}`
        tableexpenses.ajax.url(url).load()
    })
    $('#btn-remove-expense').click(() => {
        let row = tableexpenses.row($('#table-expenses tr.active')).data()
        $('body').modal({
            title: 'Confirmar',
            class: 'basic mini',
            content: '¿Estas seguro que quieres eliminar este gasto?',
            actions: [
                {text: 'Si', class: 'ok green'},
                {text: 'No', class: 'red'}
            ],
            onApprove: () => {
                var toast_info = $('body').toast({
                    class: 'info',
                    message: 'Estamos procesando tu solicitud <i class="asterisk loading icon"></i>',
                    displayTime:0,
                })
                $.ajax({
                    type:'POST',
                    url:'/finance/'+project+'/expenses',
                    data:{
                        'csrfmiddlewaretoken':getCookie('csrftoken'),
                        'to_do':'remove',
                        'id_expense':row.id
                    },
                    success: (xhr) => {
                        toast_info.toast('close')
                        $('body').toast({
                            class: 'success',
                            message: xhr.msj
                        })
                        tableexpenses.ajax.reload()
                    },
                    error: (xhr) => {
                        toast_info.toast('close')
                        error_message(xhr)
                    },
                })
            }
        }).modal('show');
    })
    $('#table-expenses tbody').on('click','tr',function(){
        $('#table-expenses tr.active').removeClass('active')
        $(this).addClass('active')
        let row = tableexpenses.row(this).data()
        $('#btn-remove-expense').removeClass('disabled')
        
    })
    $('#btn-add-expense').click(function(){
        $('#modal-new-expense').modal('show')
        $('.ui.calendar').calendar({
            type: 'date',
            text: calendar_spanish(),
        })
    })
    $('#form-new-expense').submit(function(e){
        e.preventDefault();
        $(this).addClass('double teal loading')
        let dataform = new FormData(this)
        dataform.append('to_do','create')
        $.ajax({
            type:'POST',
            url:'/finance/'+project+'/expenses',
            data:dataform,
            contentType:false,
            processData:false,
            success: (xhr) => {
                $('body').toast({
                    class: xhr.cls,
                    message: xhr.msj
                })
                $('#div_id_date').calendar('clear')
                tableexpenses.ajax.reload()
                $('#modal-new-expense').modal('hide')
                $('#form-new-expense').trigger('reset')
            },
            error: (xhr) => {
                error_message(xhr)
            },
            complete: () => {
                $('#form-new-expense').removeClass('double teal loading')
            }
        })
    })
    
});