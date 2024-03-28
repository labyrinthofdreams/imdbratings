"""
Calculate IMDb rating scores
"""
import argparse
import sys
import os.path
import csv
import logging
try:
    # mean, median, standard deviation
    import numpy
    from objsort import objsort
except Exception, e:
    print e
    sys.exit(0)

logformatter = logging.Formatter('%(asctime)s %(message)s')
fh = logging.FileHandler('ratings.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logformatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

genres = ['action', 'adventure', 'animation', 'biography',
            'comedy', 'crime', 'documentary', 'drama',
            'family', 'fantasy', 'film_noir', 'game_show',
            'history', 'horror', 'music', 'musical',
            'mystery', 'news', 'reality_tv', 'romance',
            'sci-fi', 'sport', 'talk-show', 'thriller',
            'western']

title_types = ['feature', 'docu', 'short', 'video', 'tvmovie',
                'tvseries', 'tvepisode', 'miniseries']

# Duplicate each element with (a)scending and (d)escending prefix
sortchoices=[prefix+elem for elem in ['mean', 'median', 'std', 'numvoters', 'imdbvotes',
        'imdbrating', 'runtime', 'year', 'title', 'directors'] for prefix in ('a', 'd')]
# Parse command line arguments
opts = argparse.ArgumentParser()
opts.add_argument('indir')
opts.add_argument('outfile')
opts.add_argument('--sort-by', dest='sortby', help='Sort output by one or more fields. Order matters. a = Ascending, d = Descending',
                    choices=sortchoices, nargs='+')
opts.add_argument('--diffs-file', dest='diffsfile', help='Calculate ranking differences from this file.')
opts.add_argument('--discard', dest='numdiscard', metavar='N', help='Discard N entries from top')
opts.add_argument('--limit-entries-noties', dest='limitentriesnoties',
                    type=int, help='Limit results by exact number of entries (break ties, if any)')
opts.add_argument('--limit-entries', dest='limitentries',
                    type=int, help='Limit results by number of entries without breaking a tie')
opts.add_argument('--limit-rank', dest='limitrank',
                    type=int, help='Limit results by minimum rank')
opts.add_argument('--limit-year-min', dest='limityearmin',
                    type=int, help='Limit results by min year')
opts.add_argument('--limit-year-max', dest='limityearmax',
                    type=int, help='Limit results by max year')
opts.add_argument('--limit-mean', dest='limitmean',
                    type=float, help='Limit results by minimum mean (average)')
opts.add_argument('--limit-median', dest='limitmedian',
                    type=float, help='Limit results by minimum median')
opts.add_argument('--limit-std', dest='limitstd',
                    type=float, help='Limit results by minimum standard deviation')
opts.add_argument('--limit-voters-min', dest='limitvotersmin',
                    type=int, help='Limit results by minimum number of voters')
opts.add_argument('--limit-voters-max', dest='limitvotersmax',
                    type=int, help='Limit results by maximum number of voters')
opts.add_argument('--limit-runtime-min', dest='limitruntimemin',
                    type=int, help='Limit results by minimum runtime')
opts.add_argument('--limit-runtime-max', dest='limitruntimemax',
                    type=int, help='Limit results by maximum runtime')
opts.add_argument('--limit-imdbvotes-min', dest='limitimdbvotesmin',
                    type=int, help='Limit results by minimum number of IMDb votes')
opts.add_argument('--limit-imdbvotes-max', dest='limitimdbvotesmax',
                    type=int, help='Limit results by maximum number of IMDb votes')
opts.add_argument('--limit-imdbrating-min', dest='limitimdbratingmin',
                    type=int, help='Limit results by minimum IMDb rating')
opts.add_argument('--limit-imdbrating-max', dest='limitimdbratingmax',
                    type=int, help='Limit results by maximum IMDb rating')
opts.add_argument('--limit-titletype', dest='limittitletype',
                    nargs='+', help='Limit results by title type (one or more)',
                    choices=title_types)
opts.add_argument('--limit-genre', dest='limitgenre',
                    nargs='+', help='Limit results by genre (one or more). Only one needs to match.',
                    choices=genres)

args = opts.parse_args()

while os.path.isfile(args.outfile):
    answer = raw_input('File {0} exists. Overwrite [Y/N]? '.format(args.outfile))
    if answer.lower() in ['y', 'yes']:
        break
    else:
        args.outfile = raw_input('Input path to new output file: ')

class IMDbCSVEntry:
    def __init__(self, position, imdbid, title, titletype, directors,
                 userrating, imdbrating, runtime, year, genres, imdbvotes,
                 username):
        self.imdbid = imdbid
        self.title = title
        self.titletype = titletype
        self.directors = directors
        self.imdbrating = float(imdbrating) if imdbrating else None
        self.runtime = int(runtime) if runtime else None
        self.year = int(year) if (year and year != '????') else None
        self.genres = genres.split(', ')
        self.imdbvotes = int(imdbvotes) if imdbvotes else None
        self.userratings = [int(userrating)]
        self.positions = [int(position)]
        self.users = [username]
        self.mean = 0.0
        self.median = 0
        self.std = 0.0
        self.ranking = 0
        self.numvoters = 0
        self.diff = None
    def merge(self, entry):
        """Merge two Entry objects"""
        self.userratings.extend(entry.userratings)
        self.positions.extend(entry.positions)
        self.users.extend(entry.users)
    def header(self):
        """Returns a header for the output file. Order should match to_list()"""
        return ['Ranking', 'Diff', 'Title', 'Year', 'Directors', 'Mean',
                'Median', 'Std deviation', 'Num voters', 'Runtime (mins)',
                'IMDb rating', 'IMDb votes', 'Title type', 'Genres', 'IMDb id',
                'Users']
    def to_list(self):
        return [self.ranking, self.diff, self.title, self.year, self.directors,
                self.mean, self.median, self.std, self.numvoters,
                self.runtime, self.imdbrating, self.imdbvotes, self.titletype,
                ','.join(self.genres), self.imdbid, ','.join(self.users)]

class RawEntry:
    def __init__(self, ranking, diff, title, year, directors, mean, median, std,
                 numvoters, runtime, imdbrating, imdbvotes, titletype, genres,
                 imdbid, users):
        self.imdbid = imdbid
        self.title = title
        self.titletype = titletype
        self.directors = directors
        self.imdbrating = float(imdbrating) if imdbrating else None
        self.runtime = int(runtime) if runtime else None
        self.year = int(year) if year else None
        self.genres = genres
        self.imdbvotes = int(imdbvotes) if imdbvotes else None
        self.users = users
        self.mean = mean
        self.median = median
        self.std = std
        self.ranking = int(ranking)
        self.numvoters = numvoters
        self.diff = diff
    def header(self):
        """Returns a header for the output file. Order should match to_list()"""
        return ['Ranking', 'Diff', 'Title', 'Year', 'Directors', 'Mean',
                'Median', 'Std deviation', 'Num voters', 'Runtime (mins)',
                'IMDb rating', 'IMDb votes', 'Title type', 'Genres', 'IMDb id',
                'Users']
    def to_list(self):
        return [self.ranking, self.diff, self.title, self.year, self.directors,
                self.mean, self.median, self.std, self.numvoters,
                self.runtime, self.imdbrating, self.imdbvotes, self.titletype,
                self.genres, self.imdbid, self.users]

def get_header():
    """Returns a header for the output file. Order should match to_list()"""
    return ['Ranking', 'Diff', 'Title', 'Year', 'Directors', 'Mean',
            'Median', 'Std deviation', 'Num voters', 'Runtime (mins)',
            'IMDb rating', 'IMDb votes', 'Title type', 'Genres', 'IMDb id',
            'Users']


def get_files(path):
    """Return all files in given path"""
    files = []
    for dirname, dirnames, filenames in os.walk(args.indir):
        for filename in filenames:
            files.append((dirname, filename))
    # Put partial files last
    # A partial file is a file that may be missing some fields
    partials = []
    for entry in files:
        if 'partial' in entry[1]:
            idx = files.index(entry)
            partials.append(files.pop(idx))
    files.extend(partials)
    return files

def imdb_csv_parser(infile, filename):
    """Takes a file handle, parses the file,
        and yields an Entry object representing a row"""
    reader = csv.reader(infile)
    # Skip header
    reader.next()
    for l in reader:
        try:
            if l[8] == '0':
                raise Exception('Rating cannot be zero')
            e = IMDbCSVEntry(l[0], l[1], l[5], l[6], l[7], l[8], l[9], l[10], l[11], l[12], l[13], filename.replace('.partial', ''))
            # Return Entry object
            yield e
        except Exception as err:
            logger.error('Error reading CSV file (%s line %s): %s  %s',
                            filename, l[0], str(err), ','.join(l))

def calculate_rankings(iterable, member, order='d'):
    """Calculate ranking for the list iterable based on some member and order"""
    last = None
    rank = 0
    tierank = 0
    for e in iterable:
        rank += 1
        cmpval = getattr(e, member)
        change = cmpval < last if order == 'd' else cmpval > last
        if change or not last:
            e.ranking = rank
            last = cmpval
            tierank = rank
        else:
            e.ranking = tierank

def main():
    entries = {}
    for fileparts in get_files(args.indir):
        filename = fileparts[1]
        parentdir = fileparts[0]
        fullpath = os.path.join(parentdir, filename)
        with open(fullpath, 'rb') as f:
            # Parse entries
            try:
                for entry in imdb_csv_parser(f, os.path.splitext(filename)[0]):
                    if entries.has_key(entry.imdbid):
                        entries[entry.imdbid].merge(entry)
                    else:
                        entries[entry.imdbid] = entry
            except Exception, e:
                print e
                print 'While parsing', filename

    # Copy entries from dictionary (non-deep)
    listentries = entries.values()

    # Calculate missing values
    for e in listentries:
        e.mean = numpy.mean(e.userratings)
        e.median = numpy.median(e.userratings)
        e.std = numpy.std(e.userratings)
        e.numvoters = len(e.users)

    #
    # Limit entries
    #
    # By year
    if args.limityearmin:
        listentries = filter(lambda e: e.year >= args.limityearmin, listentries)
    if args.limityearmax:
        listentries = filter(lambda e: e.year <= args.limityearmax, listentries)

    # By mean/median/standard deviation
    if args.limitmean:
        listentries = filter(lambda e: e.mean >= args.limitmean, listentries)
    if args.limitmedian:
        listentries = filter(lambda e: e.median >= args.limitmedian, listentries)
    if args.limitstd:
        listentries = filter(lambda e: e.std >= args.limitstd, listentries)

    # By number of voters
    if args.limitvotersmin:
        listentries = filter(lambda e: e.numvoters >= args.limitvotersmin, listentries)
    if args.limitvotersmax:
        listentries = filter(lambda e: e.numvoters <= args.limitvotersmax, listentries)

    # By runtime
    if args.limitruntimemin:
        listentries = filter(lambda e: e.runtime >= args.limitruntimemin, listentries)
    if args.limitruntimemax:
        listentries = filter(lambda e: e.runtime <= args.limitruntimemax, listentries)

    # By IMDb votes
    if args.limitimdbvotesmin:
        listentries = filter(lambda e: e.imdbvotes >= args.limitimdbvotesmin, listentries)
    if args.limitimdbvotesmax:
        listentries = filter(lambda e: e.imdbvotes <= args.limitimdbvotesmax, listentries)

    # By IMDb rating
    if args.limitimdbratingmin:
        listentries = filter(lambda e: e.imdbrating >= args.limitimdbratingmin, listentries)
    if args.limitimdbratingmax:
        listentries = filter(lambda e: e.imdbrating <= args.limitimdbratingmax, listentries)

    # By title type
    if args.limittitletype:
        # Replace command line values
        realtypes = {'feature': 'Feature Film', 'docu': 'Documentary',
                     'short': 'Short Film',     'video': 'Video',
                     'tvmovie': 'TV Movie',     'tvseries': 'TV Series',
                     'tvepisode': 'TV Episode', 'miniseries': 'Mini-Series'}
        titletypes = [x if not realtypes.has_key(x) else realtypes[x] for x in args.limittitletype]
        listentries = filter(lambda e: e.titletype in titletypes, listentries)

    # By genre
    if args.limitgenre:
        def has_common(lhs, rhs):
            return len(set(lhs).intersection(set(rhs)))
        listentries = filter(lambda e: has_common(e.genres, args.limitgenre),
                                listentries)

    #
    # Sort entries
    #
    if args.sortby:
        try:
            sortby = [(x[1:], x[0]) for x in args.sortby]
            objsort(listentries, sortby)
        except Exception, e:
            print e
            sys.exit()

    #
    # Calculate rankings
    #
    # Note: Rankings are calculated based on the first member passed to
    # --sort-by, otherwise 'mean' is assumed as default
    if args.sortby:
        first = args.sortby[0]
        member = first[1:]
        order = first[0]
        calculate_rankings(listentries, member, order)
    else:
        calculate_rankings(listentries, 'mean')

    # Lastly, limit by number of entries / ranking
    if args.limitentries:
        tmp = []
        for e in listentries:
            if e.ranking <= args.limitentries:
                tmp.append(e)
            else:
                break
        listentries = tmp
    if args.limitentriesnoties:
        listentries = listentries[0:args.limitentriesnoties]
    if args.limitrank:
        # Use a loop since our list is sorted it's more efficient
        # as we can break immediately after first false result
        tmp = []
        for e in listentries:
            if e.ranking >= args.limitrank:
                tmp.append(e)
            else:
                break
        listentries = tmp

    # Get entries from diffs file
    if args.diffsfile:
        diffentries = {}
        with open(args.diffsfile, 'rb') as f:
            reader = csv.reader(f)
            # Skip header
            reader.next()
            for l in reader:
                e = RawEntry(l[0], l[1], l[2], l[3], l[4], l[5], l[6], l[7], l[8], l[9], l[10], l[11], l[12], l[13], l[14], l[15])
                diffentries[e.imdbid] = e
        # Calculate differences
        for e in listentries:
            # Find entry in old entries
            if diffentries.has_key(e.imdbid):
                e.diff = diffentries[e.imdbid].ranking - e.ranking

    # Discard entries from top
    if args.numdiscard:
        skipentries = int(args.numdiscard)
        listentries = filter(lambda x: x.ranking > skipentries, listentries)

    # Write back to CSV file
    with open(args.outfile, 'wb') as out:
        writer = csv.writer(out)
        # Write header
        writer.writerow(get_header())
        for entry in listentries:
            writer.writerow(entry.to_list())

if __name__ == '__main__':
    main()