def objsort(iterable, mems):
    """Takes a list of objects and sorts them by their members in the list
        mems as tuples of member name with a character (a)scending or
        (d)escending specifying the order.

        Ex: objsort(mylist, [('year', 'a'), ('title', 'd')])
        - Sorts a list of objects by members year and title by first
        ordering the objects by year in ascending order and for matching
        years then sorts the objects by title in descending order"""
    def _objsort(iterable, mems, rmems = None):
        def _eq(lhs, rhs, rmems):
            """Takes two objects lhs and rhs and compares all members rmems
                for equality in both objects"""
            if rmems is None:
                return True
            else:
                equal = True
                for mem in rmems:
                    if getattr(lhs, mem) != getattr(rhs, mem):
                        equal = False
                        break
                return equal

        def _cmp(lhs, rhs, mem, order):
            """Compares members in two objects lhs and rhs in (a)scending
                or (d)escending order"""
            if order == 'a':
                result = cmp(getattr(lhs, mem), getattr(rhs, mem))
            else:
                result = cmp(getattr(rhs, mem), getattr(lhs, mem))
            return result

        try:
            if not mems:
                return
            first = mems[0]
            member = first[0]
            order = first[1]
            # Two objects are sorted if all the members in rmems match
            # between the two objects, otherwise they're considered equal
            iterable.sort(cmp=lambda lhs, rhs: _cmp(lhs, rhs, member, order) if _eq(lhs, rhs, rmems) else 0)
            newrmems = []
            if rmems:
                newrmems.extend(rmems)
            newrmems.append(member)
            _objsort(iterable, mems[1:], newrmems)
        except:
            raise

    _objsort(iterable, mems)