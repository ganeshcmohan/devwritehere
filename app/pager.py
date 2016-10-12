from math import ceil

class Pager(object):

    def __init__(self, page, per_page, all_objs, q='', user_id=''):
        self.q = q
        self.user_id = user_id
        self.per_page = per_page
        self.all_objs = all_objs
        self.total_count = all_objs.count()
        m = (page - 1) * per_page
        n = page * per_page
        self.objs = all_objs[m:n]
        self.page_count = int(ceil(self.total_count / float(per_page)))
        page = int(page)
        if page < 1:
            page = 1
        elif page > self.page_count:
            page = self.page_count
        self.page = page

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.page_count

    def pages(self):
        N = self.page_count
        i = self.page
        if N <= 18:
            page_range = range(1, N + 1)
        else:
            if i <= 8:
                r1 = [1, 2, 3, 4, 5, 6, 7, 8, 9]
                r2 = [N - 2, N - 1, N]
                page_range = r1 + [0] + r2
            elif i >= N - 7:
                r1 = [1, 2, 3]
                r2 = [N - 8, N - 7, N - 6, N - 5, N - 4, N - 3, N - 2, N - 1, N]
                page_range = r1 + [0] + r2
            else:
                r1 = [1, 2, 3]
                r2 = [i - 2, i - 1, i, i + 1, i + 2]
                r3 = [N - 2, N - 1, N]
                page_range = r1 + [0] + r2 + [0] + r3
        return page_range
