document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type=text]').forEach( node => node.addEventListener('keypress', e => {
      if(e.keyCode == 13) {
        e.preventDefault();
      }
    }))
  });
function calendar_spanish() {
    let text = {
        days: ['D', 'L', 'M', 'X', 'J', 'V', 'S'],
        months: ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
            'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ],
        monthsShort: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep',
            'Oct', 'Nov', 'Dic'
        ],
        today: 'Hoy',
        now: 'Ahora',
    }
    return text
}

const CONTEXT_MENU_SELECTORS = '#popup-collab, #popup-incomes, #popup-budget, #popup-clients';

function resolveCalendarElements(target) {
    if (!target) {
        return $('.ui.calendar');
    }
    const $target = $(target);
    if (!$target.length) {
        return $();
    }
    if ($target.first().hasClass('calendar')) {
        return $target;
    }
    return $target.find('.ui.calendar');
}

function hideContextMenus() {
    $(CONTEXT_MENU_SELECTORS)
        .removeClass('transition visible animating')
        .css({ visibility: '', left: '', top: '' });
}

function getContextMenuSize($popup) {
    $popup.addClass('visible').css({
        visibility: 'hidden',
        left: '-9999px',
        top: 0,
    });
    const size = {
        height: $popup.outerHeight(),
        width: $popup.outerWidth(),
    };
    hideContextMenus();
    return size;
}

function hideAllCalendars() {
    $('.ui.calendar').each(function () {
        const $cal = $(this);
        if ($cal.data('moduleCalendar')) {
            $cal.calendar('hide');
        }
    });
}

function initAppCalendar(target, options) {
    const $elements = resolveCalendarElements(target);
    const userOptions = options || {};
    const userOnSelect = userOptions.onSelect;
    const settings = $.extend({
        type: 'date',
        text: calendar_spanish(),
        context: 'body',
    }, userOptions, {
        onSelect: function (date, mode) {
            $(this).calendar('hide');
            if (typeof userOnSelect === 'function') {
                userOnSelect.call(this, date, mode);
            }
        },
    });

    $elements.each(function () {
        const $el = $(this);
        if ($el.data('moduleCalendar')) {
            $el.calendar('destroy');
        }
        $el.calendar(settings);
    });
    return $elements;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function exportTableToExcel(tableID, filename = 'export'){
    var downloadLink;
    var dataType = 'application/vnd.ms-excel';
    var tableSelect = document.getElementById(tableID);
    var tableHTML = tableSelect.outerHTML.replace(/ /g, '%20');
    
    // Specify file name
    filename = filename?filename+'.xls':'excel_data.xls';
    
    // Create download link element
    downloadLink = document.createElement("a");
    
    document.body.appendChild(downloadLink);
    
    if(navigator.msSaveOrOpenBlob){
        var blob = new Blob(['\ufeff', tableHTML], {
            type: dataType
        });
        navigator.msSaveOrOpenBlob( blob, filename);
    }else{
        // Create a link to the file
        downloadLink.href = 'data:' + dataType + ', ' + tableHTML;
    
        // Setting the file name
        downloadLink.download = filename;
        
        //triggering the function
        downloadLink.click();
    }
}

function new_message(type,title,message,unique=false) {
    if (unique){
        $('.message').remove()
    }
    $('#message-container').append(
        `<div class="ui ${type} floating message">
        <i class="close icon"></i>
        <div class="header">
            ${title}
        </div>
          ${message}
      </div>`
    )
    $('.message .close')
    .on('click', function () {
        let item = $(this)
            .parent('div.message')
            .transition('fade');
            
        item.remove()
    });
}
function error_message(xhr) {
    let code = xhr.status
    if (code==403) error_description = 'No tienes privilegios suficientes para hacer esto.' 
    else if (code == 404) error_description = 'La url solicitada no existe' 
    else if (code == 500) {
        error_description = 'Ocurrió un error procesando la solicitud, contacta al administrador del sistema' 
        console.log(xhr.responseText)
    }
    $('.message').remove()
    $('#message-container').append(
        `<div class="ui error floating message">
        <i class="close icon"></i>
        <div class="header">
            Ups!
        </div>
          ${error_description}
      </div>`
    )
    $('.message .close')
    .on('click', function () {
        let item = $(this)
            .parent('div.message')
            .transition('fade');
            
        item.remove()
    });
}
$('#principal-submenu .dropdown')
            .dropdown()
        ;
$('.message .close')
    .on('click', function () {
        $(this)
            .closest('.message')
            .transition('fade');
    });
$('#sidebar-closer').click(function () {
    var sidebar = $('#principal-sidebar')
    
    if (sidebar.hasClass('visible')) {
        sidebar.removeClass('visible')
        $('#main-segment').css('width', '99vw')
        .css('left','0px')
        $('#principal-submenu').addClass('inverted')
    } else {
        
        $('#main-segment').css('width', 'calc(100vw - 160px)')
        .css('left','150px')
        sidebar.addClass('visible')
        $('#principal-submenu').removeClass('inverted')
    }
});

$('#principal-submenu a.item.submenu').click(function () {
    $('#principal-submenu a.item.submenu').removeClass('active')
    let item = $(this)
    item.addClass('active')
})

$('#principal-sidebar a.item').hover(
    function(e){
        $('.subsidebar').removeClass('visible')
        let subsidebar = $(e.target).data('subsidebar')
        if (subsidebar == undefined) {
            $('.subsidebar').removeClass('visible')
            $('.pusher').first().removeClass('dimmed')
            return
        };
        $('.pusher').first().addClass('dimmed')
        $(subsidebar).addClass('visible')
    },
    function(){
      return
    },
  )
  $('.subsidebar').mouseleave(function(){
    $(this).removeClass('visible')
    $('.pusher').first().removeClass('dimmed')
  })
  $(document).ready(function(){
    hideContextMenus();
    $(document).on('click', function () {
        hideContextMenus();
    });
    $(document).on('keydown', function (e) {
        if (e.keyCode === 27) {
            hideContextMenus();
            hideAllCalendars();
        }
    });
  })