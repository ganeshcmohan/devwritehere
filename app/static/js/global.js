// ajax form
$('form[data-async]').on('submit', function(event) {
    var $form = $(this);
    var $target = $($form.attr('data-target'));

    $.ajax({
        type: $form.attr('method'),
        url: $form.attr('action'),
        data: $form.serialize(),
        success: function(data, status) {
            $target.attr('class',data.class).html(data.message);
        }
    });

    event.preventDefault();
});

//pjax
$.pjax.defaults.scrollTo = false;

function on_pjax(){
    $(document).pjax('a.pjax', '#pjax');
    $('#lightbox').scrollTop(0);
    $('#pjax-close').click(lightbox_close);
    $('#pjax').click(function(e){
        if (e.target == this){
            lightbox_close(e);
        }
    });
};

$(document).on('pjax:beforeSend', function() {
    $('body').addClass('noscroll');
    $('#lightbox').show();
});

$(document).on('pjax:send', function() {
    $('.loading-container').show();
});

$(document).on('pjax:complete', function() {
   $('.loading-container').hide();
   on_pjax();
});

$(document).on('pjax:timeout', function(e) {
    e.preventDefault();
});

$(document).on('pjax:error', function(e) {
    e.preventDefault();
});

function lightbox_close(e) {
    $('body').removeClass('noscroll');
    $('#lightbox').hide();
    $('#pjax').html('');
    history.pushState({},'',g_url_back);
};

$(document).keyup(function(e) {
    if (e.keyCode == 27) { 
        lightbox_close(e);
    }
});
