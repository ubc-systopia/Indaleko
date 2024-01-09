
class IndalekoWindows:

    FILE_ATTRIBUTES = {
        'FILE_ATTRIBUTE_READONLY' : 0x00000001,
        'FILE_ATTRIBUTE_HIDDEN' : 0x00000002,
        'FILE_ATTRIBUTE_SYSTEM' : 0x00000004,
        'FILE_ATTRIBUTE_DIRECTORY' : 0x00000010,
        'FILE_ATTRIBUTE_ARCHIVE' : 0x00000020,
        'FILE_ATTRIBUTE_DEVICE' : 0x00000040,
        'FILE_ATTRIBUTE_NORMAL' : 0x00000080,
        'FILE_ATTRIBUTE_TEMPORARY' : 0x00000100,
        'FILE_ATTRIBUTE_SPARSE_FILE' : 0x00000200,
        'FILE_ATTRIBUTE_REPARSE_POINT' : 0x00000400,
        'FILE_ATTRIBUTE_COMPRESSED' : 0x00000800,
        'FILE_ATTRIBUTE_OFFLINE' : 0x00001000,
        'FILE_ATTRIBUTE_NOT_CONTENT_INDEXED' : 0x00002000,
        'FILE_ATTRIBUTE_ENCRYPTED' : 0x00004000,
        'FILE_ATTRIBUTE_INTEGRITY_STREAM' : 0x00008000,
        'FILE_ATTRIBUTE_VIRTUAL' : 0x00010000,
        'FILE_ATTRIBUTE_NO_SCRUB_DATA' : 0x00020000,
        'FILE_ATTRIBUTE_EA' : 0x00040000,
        'FILE_ATTRIBUTE_PINNED' : 0x00080000,
        'FILE_ATTRIBUTE_UNPINNED' : 0x00100000,
        'FILE_ATTRIBUTE_RECALL_ON_OPEN' : 0x00040000,
        'FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS' : 0x00400000,
        'FILE_ATTRIBUTE_STRICTLY_SEQUENTIAL' : 0x20000000,
        'FILE_ATTRIBUTE_OPEN_REPARSE_POINT' : 0x00200000,
        'FILE_ATTRIBUTE_OPEN_NO_RECALL' : 0x00100000,
        'FILE_ATTRIBUTE_FIRST_PIPE_INSTANCE' : 0x00080000,
    }

    @staticmethod
    def map_file_attributes(attributes : int):
        fattrs = []
        if (0 == attributes):
            fattrs = ['FILE_ATTRIBUTE_NORMAL']
        for attr in IndalekoWindows.FILE_ATTRIBUTES:
            if attributes & IndalekoWindows.FILE_ATTRIBUTES[attr] == IndalekoWindows.FILE_ATTRIBUTES[attr]:
                fattrs.append(attr)
        return ' | '.join(fattrs)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Indaleko Windows test logic')
    parser.add_argument('--attr', '-a', default = 0xFFFFFFFF, type = int, help = 'file attribute bits to test')
    args = parser.parse_args()
    if (args.attr == 0xFFFFFFFF):
        print('Testing all attributes')
        for attr in IndalekoWindows.FILE_ATTRIBUTES:
            print(f'{attr} = {IndalekoWindows.FILE_ATTRIBUTES[attr]}')
            print(f'{attr} = {IndalekoWindows.map_file_attributes(IndalekoWindows.FILE_ATTRIBUTES[attr])}')
    else:
        print(f'{args.attr} = {IndalekoWindows.map_file_attributes(args.attr)}')

if __name__ == '__main__':
    main()
