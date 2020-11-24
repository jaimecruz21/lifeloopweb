const Disqus = function () {
    let $container_mobile,
        $container_desktop,
        breakpoint = 1200,
        page,
        sso,
        url = 'lifelooplive.disqus.com';

    const init = function () {
        $container_desktop = $('#disqus_thread_desktop');
        $container_mobile = $('#disqus_thread_mobile');

        page = $container_desktop.data('page');
        sso = $container_desktop.data('sso');

        window.disqus_config = function() {
            this.page.remote_auth_s3 = page.remote_auth_s3;
            this.page.api_key = page.api_key;
            this.page.url = page.url;
            this.page.identifier = page.identifier;
            this.sso = sso;
        };

        $(window).on('resize', onResize);
        $(window).resize();
    };

    const onResize = function () {
        if ($(window).width() < breakpoint) {
            $container_mobile.attr('id', 'disqus_thread');
            $container_desktop.attr('id', 'disqus_thread_desktop');
        } else {
            $container_desktop.attr('id', 'disqus_thread');
            $container_mobile.attr('id', 'disqus_thread_mobile');
        }

        load();
    };

    const load = function () {
        let d = document,
            s = d.createElement('script');
        s.src = '//' + url + '/embed.js';
        s.setAttribute('data-timestamp', +new Date());
        (d.head || d.body).appendChild(s);
    };

    return {
        init: init
    }
}();

export {Disqus};
