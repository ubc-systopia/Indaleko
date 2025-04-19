CC ?= x86_64-w64-mingw32-gcc
CFLAGS ?= -O2 -Wall
TARGET = journal

all: $(TARGET).exe

$(TARGET).exe: journal.c
	$(CC) $(CFLAGS) -o $(TARGET).exe journal.c

clean:
	rm -f $(TARGET).exe