/* prototypes */

    $.Isotope.prototype._getCenteredMasonryColumns = function() {
        this.width = this.element.width();

        var parentWidth = this.element.parent().width();

        // i.e. options.masonry && options.masonry.columnWidth
        var colW = this.options.masonry && this.options.masonry.columnWidth ||
            // or use the size of the first item
            this.$filteredAtoms.outerWidth(true) ||
            // if there's no items, use size of container
            parentWidth;

        var cols = Math.floor( parentWidth / colW );
        cols = Math.max( cols, 1 );

        // i.e. this.masonry.cols = ....
        this.masonry.cols = cols;
        // i.e. this.masonry.columnWidth = ...
        this.masonry.columnWidth = colW;
    };

    $.Isotope.prototype._masonryReset = function() {
        // layout-specific props
        this.masonry = {};
        // FIXME shouldn't have to call this again
        this._getCenteredMasonryColumns();
        var i = this.masonry.cols;
        this.masonry.colYs = [];
        while (i--) {
            this.masonry.colYs.push( 0 );
        }
    };

    $.Isotope.prototype._masonryResizeChanged = function() {
        var prevColCount = this.masonry.cols;
        // get updated colCount
        this._getCenteredMasonryColumns();
        return ( this.masonry.cols !== prevColCount );
    };

    $.Isotope.prototype._masonryGetContainerSize = function() {
        var unusedCols = 0,
            i = this.masonry.cols;
        // count unused columns
        while ( --i ) {
            if ( this.masonry.colYs[i] !== 0 ) {
                break;
            }
            unusedCols++;
        }

        return {
            height : Math.max.apply( Math, this.masonry.colYs ),
            // fit container to columns that have been used;
            width : (this.masonry.cols - unusedCols) * this.masonry.columnWidth
        };
    };

/* main */

var writehere = (function (parent, $, _) {
    var self = parent;

        self.ajax = self.ajax || undefined;
        self.skip = self.skip || 0;

        self.lastId = self.lastId || undefined;
        self.lastPage = self.lastPage || undefined;
        self.dbId = self.dbId|| undefined;
        self.lastSort = self.lastSort|| undefined;

        self.query = self.query || undefined;
        self.topicId = self.topicId || undefined;
        self.myPageUserId = self.myPageUserId || undefined;
        self.gridIds = self.gridIds || Array();

        /*
            Highlight Logic
         */

        self.setSelection = function () {
            var MIN_SELECTION_LENGTH = 10;

            if (!rangy.initialized) rangy.init();

            var selection = rangy.getSelection();
            if (selection.rangeCount === 0) return;

            var range = selection.getRangeAt(0);
            var text = range.toString();
            if (text.length < MIN_SELECTION_LENGTH) return {
                'selected': false,
                'text': '',
                'html': ''
            };

            var html = range.toHtml();

            selection.removeAllRanges();

            var isWrapped = writehere.wrapSelection(html);
            return {
                'selected': isWrapped,
                'html': html,
                'text': text
            }
        }

        self.clearSelection = function() {
            $('.highlight').contents().unwrap();
        }

        self.wrapSelection = function(phraseHtml) {
            var $selectableArea = $('.post-content');
            var containerHtml = $selectableArea.html();
		//alert(containerHtml);
		//alert(phraseHtml.replace(/&/g, "&amp;").replace(/>/g, "&gt;").replace(/</g, "&lt;").replace(/"/g, "&quot;"));
		
	    phraseHtml = phraseHtml.replace(/&/g, "&amp;").replace(/>/g, "&gt;").replace(/</g, "&lt;");

	    var startIndex = containerHtml.toLowerCase().indexOf(phraseHtml.toLowerCase());

            if (!(~startIndex)) return false;

            var phraseLength = phraseHtml.length;

            var newHtml = containerHtml.slice(0, startIndex) +
                '<span class="highlight">' + phraseHtml +
                '</span>' + containerHtml.slice(startIndex + phraseLength);

            $selectableArea.html(newHtml);

            return true;
        }

        self.loadGrid = function(selector, items) {
            var $grid = $(selector);

            var gridItemTemplate = _.template($('#gridItemTemplate').html());
            _.each(items, function(grid) {
                var html = gridItemTemplate(grid);
                $grid.isotope('insert', $(html));
                self.gridIds.push(grid['id']);
            });
        }

        self.gridAbstract = function(url, data, callback) {

        }

        self.resetGrid = function() {
            $('#gridContainer').isotope('remove', $('.grid-item:not(#aboutMe)'));
            self.gridIds = Array();
            self.lastPage = false;
            self.lastId = undefined;
            self.dbId = undefined;
            self.skip = 0;
        }

        self.hasScroll = function() {
            var cStyle = document.body.currentStyle||window.getComputedStyle(document.body, "");

            return hasVScroll = cStyle.overflow == "visible"
                || cStyle.overflowY == "visible"
                || (hasVScroll && cStyle.overflow == "auto")
                || (hasVScroll && cStyle.overflowY == "auto");
        }

        self.setGridSort = function(sort) {
            self.lastSort = sort;
        }

        self.loadIndex = function (selector, reset, sort, writers) {
            self.ajax = true;
            if (reset) self.resetGrid();
            if (self.lastPage) return;

            self.spinner(true);

            self.lastSort = sort || self.lastSort || 'latest';
            self.writers = writers || self.writers || 'everybody';

            $.ajax({ 'url': '/index/json/simple',
                'type': 'GET',
                'dataType': 'json',
                'data':  {
                    'skip': self.skip,
                    'last_page': self.lastPage,
                    'sort': self.lastSort,
                    'writers': self.writers,
                },
                'async': true,
                'success': function(data) {
                    self.lastPage = data['last_page'];
                    self.skip += 1;
                    if (data['opinions'].length > 0) {

                        if (reset) {
                            $('#gridContainer').isotope('remove', $('.grid-item:not(#aboutMe)'));
                        }

                        self.loadGrid("#gridContainer", data['opinions']);

                    } else {
                        self.lastPage = true;
                    }
                },
                'complete': function() { 
                    self.ajax = false; 
                    self.spinner(false); 
                    on_pjax();
                }
            });

            $(window).scroll(function() {
                if (self.ajax) return true;
                if (document.body.scrollHeight - $(this).scrollTop()  <= $(this).height()) {
                    self.loadIndex('#gridContainer', false);
                }
            });

        }

        self.load_grid = function(selector, url, data) {
            console.log(url);
            console.log(data);
            self.ajax = true;
            reset = true;//TODO
            if (reset) self.resetGrid();
            if (self.lastPage) return;

            self.spinner(true);

            var sortMethod = self.lastSort || 'latest';
            data.skip = self.skip;

            $.get(url,data,function(data) {
                self.ajax = false;
                self.lastPage = data['last_page'];
                self.skip += 1;
                if (data['opinions'].length > 0) {
                    if (reset) {
                        $('#gridContainer').isotope('remove', $('.grid-item:not(#aboutMe)'));
                    }
                    self.loadGrid("#gridContainer", data['opinions']);

                    if (self.ajax) {
                        return true;
                    }

                } else {
                    self.lastPage = true;
                }
            }).done(function() { 
                self.ajax = false; 
                self.spinner(false); 
                on_pjax();
            });

            $(window).scroll(function() {
                if (self.ajax) return true;
                if (document.body.scrollHeight - $(this).scrollTop()  <= $(this).height()) {
                    self.loadGeneric('#gridContainer', url, id, false);
                }
            });

        }

        self.loadGeneric = function(selector, url, id, reset, sort, writers) {
            self.ajax = true;
            if (reset) self.resetGrid();
            if (self.lastPage) return;
            self.dbId = id;

            self.spinner(true);

            self.lastSort = sort || self.lastSort || 'latest';
            self.writers = writers || self.writers || 'everybody';

            $.ajax({
                'url': url,
                'type': 'GET',
                'dataType': 'json',
                'data':  {
                    'skip': self.skip,
                    'last_page': self.lastPage,
                    'sort': self.lastSort,
                    'writers': self.writers,
                    'id': self.dbId
                },
                'async': true,
                'success': function(data) {
                    self.ajax = false;
                    self.lastPage = data['last_page'];
                    self.skip += 1;
                    if (data['opinions'].length > 0) {
                        if (reset) {
                            $('#gridContainer').isotope('remove', $('.grid-item:not(#aboutMe)'));
                        }
                        self.loadGrid("#gridContainer", data['opinions']);

                        if (self.ajax) {
                            return true;
                        }

                    } else {
                        self.lastPage = true;
                    }


                },
                'complete': function() { 
                    self.ajax = false; 
                    self.spinner(false); 
                    on_pjax();
                }

            });

            $(window).scroll(function() {
                if (self.ajax) return true;
                if (document.body.scrollHeight - $(this).scrollTop()  <= $(this).height()) {
                    self.loadGeneric('#gridContainer', url, id, false);
                }
            });

        }

        self.loadTopic = function(selector, topicId, reset) {

            self.topicId = topicId;
            $.ajax({
                'url': '/json/topic/grid',
                'type': 'GET',
                'dataType': 'json',
                'data':  {
                    'last_id': self.lastId,
                    'topic_id': self.topicId
                },
                'async': true,
                'success': function(data) {
                    if (data['opinions'].length > 0) {
                        if (reset) {
                            $('#gridContainer').isotope('remove', $('.grid-item'));
                        }
                        self.lastId = data['last_id'];
                        self.loadGrid("#gridContainer", data['opinions']);

                        if (!($(document).height() > $(window).height())) {
                            self.loadTopic('#gridContainer', self.topicId, false);
                        }
                    }
                }
            });

            $(window).scroll(function() {
                if (document.body.scrollHeight - $(this).scrollTop()  <= $(this).height()) {
                    self.loadTopic('#gridContainer', self.topicId, false);
                }
            });

        }

        self.loadMyPage = function(selector, userId, reset) {
            self.myPageUserId = userId;
            $.ajax({
                'url': '/json/my-page/grid',
                'type': 'GET',
                'dataType': 'json',
                'data':  {
                    'last_id': self.lastId,
                    'user_id': self.myPageUserId
                },
                'async': true,
                'success': function(data) {
                    if (data['opinions'].length > 0) {
                        if (reset) {
                            $('#gridContainer').isotope('remove', $('.grid-item-dummy'));
                        }
                        self.lastId = data['last_id'];
                        self.loadGrid("#gridContainer", data['opinions']);

                        if (!($(document).height() > $(window).height())) {
                            self.loadMyPage('#gridContainer', self.myPageUserId, false);
                        }
                    }
                }
            });

            $(window).scroll(function() {
                if (document.body.scrollHeight - $(this).scrollTop()  <= $(this).height()) {
                    self.loadMyPage('#gridContainer', self.myPageUserId, false);
                }
            });

        }

        /* show search results */
        self.loadSearch = function(selector, query, reset, sort, writers) {
            self.spinner(true);
            self.query = query;
            self.lastSort = sort || self.lastSort || 'latest';
            self.writers = writers || self.writers || 'everybody';
            $.ajax({
                'url': '/search/json',
                'type': 'GET',
                'dataType': 'json',
                'data':  {
                    'start': self.lastId,
                    'query': query,
                    'sort': self.lastSort,
                    'writers': self.writers,
                },
                'async': true,
                'success': function(data) {
                    if (data['opinions'].length > 0) {
                        if (reset) {
                            $('#gridContainer').isotope('remove', $('.grid-item:not(#search-grid)'));
                        }
                        self.lastId = data['start'];
                        self.loadGrid("#gridContainer", data['opinions']);
                    }
                },
                'complete': function(){
                    self.spinner(false);
                    on_pjax();
                }
            });

            $(window).scroll(function() {
                if (document.body.scrollHeight - $(this).scrollTop()  <= $(this).height()) {
                    self.loadSearch('#gridContainer', self.query, false);
                }
            });

        }

        /* autocomplete */
        self.loadAutocomplete = function(selector, url, updater) {
            //updater = updater || ;

            $(selector).typeahead({
                'menu': '<ul class="typeahead dropdown-menu dropdown-fixed dropdown-search"></ul>',
                source: url,
                itemSelected: function(url, query) {
                    if (typeof url !== 'undefined') {
                        window.location.replace(url);
                    } else {
                        window.location.replace("/search?query="+query);
                    }
                },
                items: 10
            });
        }

        self.cookiesEnabled = function() {
            var cookieEnabled = (navigator.cookieEnabled) ? true : false;

            if (typeof navigator.cookieEnabled == "undefined" && !cookieEnabled)
            {
                document.cookie="testcookie";
                cookieEnabled = (document.cookie.indexOf("testcookie") != -1) ? true : false;
            }
            return cookieEnabled;
        }

        self.spinner = function(toggle) {
            if (toggle) {
                $('.loading-container').show();
            } else {
                $('.loading-container').hide();
            }
        }

        return self;
    }(writehere || {}, jQuery, _));
