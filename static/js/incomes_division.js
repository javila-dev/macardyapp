$(document).ready(function(){
    $('.ui.dropdown').dropdown('set selected',month);
    $('#id-year-to-search').val(year)
    $('#btn-close-period').click(function(){
        let month = $('#id-month-to-search').val()
        let year = $('#id-year-to-search').val()
        if (month == "" || year == "" ){
            $('body').toast({
                class:'error',
                message: 'Debes seleccionar un mes y un año primero.',
            });
            return;
        }
        $.ajax({
            url:"/finance/"+project+"/availablecash",
            type:"GET",
            data:{
                'month-to-search':month,
                'year-to-search':year,
            },
            success: (xhr) =>{
                if (xhr.exists){
                    $('body').toast({
                        class:'error',
                        message: 'Ya existe un periodo registrado posterior al que estas intentando cerrar',
                    });
                }
                else{
                    $('#modalClosePeriod').modal('show')
                }
            }
        })
        
    })
    $('#form-avbcash').submit(function(e){
        let month = $('#id-month-to-search').val()
        let year = $('#id-year-to-search').val()
        if (month == "" || year == "" ){
            e.preventDefault();
            $('body').toast({
                class:'error',
                message: 'Debes seleccionar un mes y un año.',
            });
            return;
        }
        $('#form-avbcash button').addClass('disabled loading')
    })
    $('#form-new-cc').on('submit',function(e){
        let month = $('#id-month-to-search').val()
        let year = $('#id-year-to-search').val()
        $(this).append(`<input hidden name="month" value="${month}">`)
        $(this).append(`<input hidden name="year" value="${year}">`)
        let total_perc = 0
        $('input[name="cc_perc"]').each(function(index,element){
            total_perc += $(element).val() *1
        })
        if (total_perc > 100){
            $('body').toast({
                class:'error',
                message: 'La suma de los porcentajes no puede ser mayor a 100%',
            });
            e.preventDefault();
        }
    })
})