$("button").click(function() {
    $(".mainwrapper").animate( {scrollTop: $(".scrolltarget").offset().top - 100});
});