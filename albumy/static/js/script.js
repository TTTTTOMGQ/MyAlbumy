$(function () {
    var flash = null;

    // 这个toast函数是用来显示提示信息的，比如说上传成功，或者上传失败
    function toast(body) {
        clearTimeout(flash);
        var $toast = $('#toast');
        $toast.text(body).fadeIn();
        flash = setTimeout(function () {
            $toast.fadeOut();
        }, 3000);
    }


    var hover_timer = null;

    function show_profile_popover(e) {
        var $el = $(e.target);
        // setTimeout是用来设置定时器的
        hover_timer = setTimeout(function () {
            hover_timer = null;
            // ajax是用来向服务器发送请求的
            $.ajax({
                type: 'GET',
                url: $el.data('href'),
                success: function (data) {
                    $el.popover({
                        html: true,
                        content: data,
                        trigger: 'manual',
                        animation: false
                    });
                    $el.popover('show');
                    $('.popover').on('mouseleave', function () {
                        setTimeout(function () {
                            $el.popover('hide');
                        }, 200);
                    });
                },
                error: function (error) {
                    toast('Server error, please try again later.');
                }
            });
        }, 500);
    }

    function hide_profile_popover(e) {
        var $el = $(e.target);

        if (hover_timer) {
            // clearTimeout是用来取消定时器的
            clearTimeout(hover_timer);
            hover_timer = null;
        } else {
            setTimeout(function () {
                if (!$('.popover:hover').length) {
                    $el.popover('hide');
                }
            }, 200);
        }
    }

    $('.profile-popover').hover(show_profile_popover.bind(this), hide_profile_popover.bind(this));

    // hide or show tag edit form
    $('#tag-btn').click(function () {
        $('#tags').hide();
        $('#tag-form').show();
    });
    $('#cancel-tag').click(function () {
        $('#tag-form').hide();
        $('#tags').show();
    });
    // hide or show description edit form
    $('#description-btn').click(function () {
        $('#description').hide();
        $('#description-form').show();
    });
    $('#cancel-description').click(function () {
        $('#description-form').hide();
        $('#description').show();
    });
    // delete confirm modal
    $('#confirm-delete').on('show.bs.modal', function (e) {
        $('.delete-form').attr('action', $(e.relatedTarget).data('href'));
    });

    $("[data-toggle='tooltip']").tooltip({title: moment($(this).data('timestamp')).format('lll')})
});