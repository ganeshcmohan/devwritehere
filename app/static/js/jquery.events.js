/**
 * @depends jquery
 * @name jquery.events
 * @package jquery-sparkle
 * @author Benjamin "balupton" Lupton {@link http://www.balupton.com}
 * @copyright (c) 2009-2010 Benjamin Arthur Lupton {@link http://www.balupton.com}
 * @license GNU Affero General Public License - {@link http://www.gnu.org/licenses/agpl.html}
 */

(function($){

    var _oldhide = $.fn.hide;
    $.fn.hide = function(speed, callback) {
        $(this).trigger('hide');
        return _oldhide.apply(this,arguments);
    };

    /**
     * Bind a event, with or without data
     * Benefit over $.bind, is that $.binder(event, callback, false|{}|''|false) works.
     */
    $.fn.binder = $.fn.binder || function(event, data, callback){
        // Help us bind events properly
        var $this = $(this);
        // Handle
        if ( (callback||false) ) {
            $this.bind(event, data, callback);
        } else {
            callback = data;
            $this.bind(event, callback);
        }
        // Chain
        return $this;
    };

    /**
     * Event for the last click for a series of one or more clicks
     */
    $.fn.lastclick = $.fn.lastclick || function(data,callback){
        return $(this).binder('lastclick',data,callback);
    };
    $.event.special.lastclick = $.event.special.lastclick || {
        setup: function( data, namespaces ) {
            $(this).bind('mouseup', $.event.special.lastclick.handler);
        },
        teardown: function( namespaces ) {
            $(this).unbind('mouseup', $.event.special.lastclick.handler);
        },
        handler: function( event ) {
            // Setup
            var clear = function(){
                // Fetch
                var Me = this;
                var $el = $(Me);
                // Fetch Timeout
                var timeout = $el.data('lastclick-timeout')||false;
                // Clear Timeout
                if ( timeout ) {
                    clearTimeout(timeout);
                }
                timeout = false;
                // Store Timeout
                $el.data('lastclick-timeout',timeout);
            };
            var check = function(event){
                // Fetch
                var Me = this;
                clear.call(Me);
                var $el = $(Me);
                // Store the amount of times we have been clicked
                $el.data('lastclick-clicks', ($el.data('lastclick-clicks')||0)+1);
                // Handle Timeout for when All Clicks are Completed
                var timeout = setTimeout(function(){
                    // Fetch Clicks Count
                    var clicks = $el.data('lastclick-clicks');
                    // Clear Timeout
                    clear.apply(Me,[event]);
                    // Reset Click Count
                    $el.data('lastclick-clicks',0);
                    // Fire Event
                    event.type = 'lastclick';
                    $.event.handle.apply(Me, [event,clicks])
                },500);
                // Store Timeout
                $el.data('lastclick-timeout',timeout);
            };
            // Fire
            check.apply(this,[event]);
        }
    };

})(jQuery);


/*
 * debouncedresize: special jQuery event that happens once after a window resize
 *
 * latest version and complete README available on Github:
 * https://github.com/louisremi/jquery-smartresize
 *
 * Copyright 2012 @louis_remi
 * Licensed under the MIT license.
 *
 * This saved you an hour of work?
 * Send me music http://www.amazon.co.uk/wishlist/HNTU0468LQON
 */
(function($) {

    var $event = $.event,
        $special,
        resizeTimeout;

    $special = $event.special.debouncedresize = {
        setup: function() {
            $( this ).on( "resize", $special.handler );
        },
        teardown: function() {
            $( this ).off( "resize", $special.handler );
        },
        handler: function( event, execAsap ) {
            // Save the context
            var context = this,
                args = arguments,
                dispatch = function() {
                    // set correct event type
                    event.type = "debouncedresize";
                    $event.dispatch.apply( context, args );
                };

            if ( resizeTimeout ) {
                clearTimeout( resizeTimeout );
            }

            execAsap ?
                dispatch() :
                resizeTimeout = setTimeout( dispatch, $special.threshold );
        },
        threshold: 500
    };

})(jQuery);

//by Michalis Tzikas & Vasilis Lolos
//07-03-2012
//v1.0
/*
 Copyright (C) 2011 by Michalis Tzikas & Vasilis Lolos

 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 THE SOFTWARE.
 */
(function( $ ){
    $.fn.linker = function(options) {
        var defaults = {
            target   : '', //blank,self,parent,top
            className : '',
            rel : ''
        };
        var options = $.extend(defaults, options);

        target_string	= (options.target != '') ? 'target="_'+options.target+'"' : '';
        class_string	= (options.className != '') ? 'class="'+options.className+'"' : '';
        rel_string		= (options.rel != '') ? 'rel="'+options.rel+'"' : '';

        $(this).each(function(){
            t = $(this).text();

            t = t.replace(/(https\:\/\/|http:\/\/)([www\.]?)([^\s|<]+)/gi,'<a href="$1$2$3" '+target_string+' '+class_string+' '+rel_string+'>$1$2$3</a>');
            t = t.replace(/([^https\:\/\/]|[^http:\/\/]|^)(www)\.([^\s|<]+)/gi,'$1<a href="http://$2.$3" '+target_string+' '+class_string+' '+rel_string+'>$2.$3</a>');
            t = t.replace(/<([^a]|^\/a])([^<>]+)>/g, "&lt;$1$2&gt;").replace(/&lt;\/a&gt;/g, "</a>").replace(/<(.)>/g, "&lt;$1&gt;").replace(/\n/g, '<br />');

            $(this).html(t);
        });
    };
})( jQuery );



/*
; (function($) {
    $.fn.textfill = function(options) {
        var defaults = {
            maxFontPixels: 40,
            innerTag: 'span'
        };
        var Opts = jQuery.extend(defaults, options);
        return this.each(function() {
            var fontSize = Opts.maxFontPixels;
            var ourText = $(Opts.innerTag + ':visible:first', this);
            var maxHeight = $(this).height();
            var maxWidth = $(this).width();
            var textHeight;
            var textWidth;
            do {
                ourText.css('font-size', fontSize);
                textHeight = ourText.height();
                textWidth = ourText.width();
                fontSize = fontSize - 1;
            } while ((textHeight > maxHeight || textWidth > maxWidth) && fontSize > 3);
        });
    };
})(jQuery);

(function($) {
    $.fn.textfill = function(maxFontSize, innerElement) {
        maxFontSize = parseInt(maxFontSize, 10);
        return this.each(function(){
            var ourText = $(innerElement, this);
            if (innerElement !== 'h3 a') {
                ourText.css('whiteSpace', 'normal');
            }
            var parent = ourText.parent(),
                maxHeight = parent.height(),
                maxWidth = parent.width(),
                fontSize = parseInt(ourText.css("fontSize"), 10),
                multiplier = maxWidth/ourText.width(),
                newSize = (fontSize*(multiplier-0.1));
            ourText.animate( {
                "fontSize":
                (maxFontSize > 0 && newSize > maxFontSize) ?
                maxFontSize :
                newSize
            }, 250)
            //ourText.css(

            //);
        });
    };
})(jQuery);   */


