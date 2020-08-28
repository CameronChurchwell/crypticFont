#!/usr/bin/env python
# coding: utf-8

# In[1]:


import struct


# In[2]:


def readObject(object_type):
    if object_type == "uint32":
        return struct.unpack(">I", f.read(4))[0]
    elif object_type == "uint16":
        return struct.unpack(">H", f.read(2))[0]
    elif object_type == "uint8":
        return struct.unpack(">B", f.read(1))[0]
    elif object_type == "formal_tag":
        arr = []
        for i in range(0, 4):
            arr.append(readObject("uint8"))
        return arr
    elif object_type == "informal_tag":
        tag = ""
        for i in range(0, 4):
            tag += chr(struct.unpack(">B", f.read(1))[0])
        return tag
    else:
        raise ValueError("Type Not Understood")


# In[3]:


#debug
if "f" in globals().keys():
    f.close()
    print("File Reloaded!")

file_name = "SFNS.ttf"
#file_name = "Symbol.ttf"
f = open(file_name, "r")


# In[4]:


assert readObject("uint32") == 0x00010000


# In[5]:


numTables = readObject("uint16")
searchRange = readObject("uint16")
entrySelector = readObject("uint16")
rangeShift = readObject("uint16")


# In[6]:


tags = []
checkSums = []
offsets = []
lengths = []
for i in range(0, numTables):
    tags.append(readObject("informal_tag"))
    checkSums.append(readObject("uint32"))
    offsets.append(readObject("uint32"))
    lengths.append(readObject("uint32"))


# In[7]:


tableMemory = []
for i in range(0, numTables):
    f.seek(offsets[i])
    #tableMemory.append(f.read((lengths[i] + 3) / 4 * 4))
    tableMemory.append(f.read(lengths[i]))


# In[8]:


nameTableIndex = tags.index("name")
nameTable = tableMemory[nameTableIndex]

assert struct.unpack(">H", nameTable[0:0+2])[0] == 0

stringStorageOffset = struct.unpack(">H", nameTable[4:4+2])[0]

#in bytes
assumedNameLength = 22

#assume first record is the unicode one
assert struct.unpack(">H", nameTable[6:6+2])[0] == 0
assert struct.unpack(">H", nameTable[12:12+2])[0] == 4
assert struct.unpack(">H", nameTable[14:14+2])[0] == assumedNameLength
nameOffset = struct.unpack(">H", nameTable[16:16+2])[0]

nameStringOffset = stringStorageOffset + nameOffset

newName = "Randomized1"
newNameBinary = ""
for i in range(0, assumedNameLength / 2):
    newNameBinary += struct.pack(">H", ord(newName[i]))

print(nameTable[nameStringOffset:nameStringOffset + assumedNameLength])    

nameTable = nameTable[:nameStringOffset] + newNameBinary + nameTable[nameStringOffset+assumedNameLength:]

tableMemory[nameTableIndex] = nameTable


# In[9]:


#change the PostScript name so that the font is not picked up as a system font (oops)

#assume index is 27
psNameIndex = 27

psNameRecordOffset = 6 + 12 * psNameIndex #6 byte header and 12 byte subTables

assert struct.unpack(">H", nameTable[psNameRecordOffset+6:psNameRecordOffset+6+2])[0] == 6 #check if psName

assumedPsNameLength = 26

assert struct.unpack(">H", nameTable[psNameRecordOffset+8:psNameRecordOffset+8+2])[0] == assumedPsNameLength

psNameOffset = struct.unpack(">H", nameTable[psNameRecordOffset+10:psNameRecordOffset+10+2])[0]

psNameStringOffset = stringStorageOffset + psNameOffset

newPsName = ".RandomizedV1"
newPsNameBinary = ""
for i in range(0, assumedPsNameLength / 2):
    newPsNameBinary += struct.pack(">H", ord(newPsName[i]))
    
nameTable = nameTable[:psNameStringOffset] + newPsNameBinary + nameTable[psNameStringOffset+assumedPsNameLength:]

tableMemory[nameTableIndex] = nameTable


# In[10]:


newNameTable = nameTable[0:0+2] #copy format bytes

newNumNames = 2

newNameTable += struct.pack(">H", newNumNames) #count
newNameTable += struct.pack(">H", 6 + newNumNames * 12) #stringOffset

#nameRecords
curIdx = 0 #current name index
curOff = 6 + 12 * curIdx
newNameTable += nameTable[curOff:curOff+10]
newNameTable += struct.pack(">H", 0) #OFFSET

curIdx = psNameIndex #current name index
curOff = 6 + 12 * curIdx
newNameTable += nameTable[curOff:curOff+10]
newNameTable += struct.pack(">H", assumedNameLength)

newNameTable += newNameBinary
newNameTable += newPsNameBinary

tableMemory[nameTableIndex] = newNameTable


# In[11]:


cmap_index = tags.index("cmap")
cmap_table = tableMemory[cmap_index]

assert struct.unpack(">H", cmap_table[0:0+2])[0] == 0
assert struct.unpack(">H", cmap_table[2:2+2])[0] == 4

assert struct.unpack(">H", cmap_table[12:12+2])[0] == 0
assert struct.unpack(">H", cmap_table[14:14+2])[0] == 4
cmap12_offset = struct.unpack(">I", cmap_table[16:16+4])[0]

#obtain original group data

cmap12_length = struct.unpack(">I", cmap_table[cmap12_offset+4:cmap12_offset+4+4])[0]
cmap12 = cmap_table[cmap12_offset:cmap12_offset+cmap12_length]
cmap12_nGroups = struct.unpack(">I", cmap12[12:12+4])[0]

#parse original group data
cmap12_groups = cmap12[16:]
startCharCodes = []
endCharCodes = []
startGlyphCodes = []
for i in range(0, cmap12_nGroups):
    group_index = i * 12
    startCharCodes.append(struct.unpack(">I", cmap12_groups[group_index:group_index+4])[0])
    endCharCodes.append(struct.unpack(">I", cmap12_groups[group_index+4:group_index+4+4])[0])
    startGlyphCodes.append(struct.unpack(">I", cmap12_groups[group_index+8:group_index+4+8])[0])

#create mapping for latin characters in question

def charToGlyph(charCode):
    group = None
    for i in range(0, len(endCharCodes)):
        if endCharCodes[i] >= charCode:
            group = i
            break
    return startGlyphCodes[group] + (charCode - startCharCodes[group])

latinUppercase = range(65, 90 + 1) #+1 because range upper bound not inclusive
latinUppercaseGlyphs = []
for charCode in latinUppercase:
    latinUppercaseGlyphs.append(charToGlyph(charCode))
print(latinUppercaseGlyphs)

latinLowercase = range(97, 122 + 1) #+1 because range upper bound not inclusive
latinLowercaseGlyphs = []
for charCode in latinLowercase:
    latinLowercaseGlyphs.append(charToGlyph(charCode))
print(latinLowercaseGlyphs)


#create shuffle key
from random import shuffle

shuffle_key = range(0, 26)
shuffle(shuffle_key)

#Shuffle glyphs
latinUpperShuffled = []
latinLowerShuffled = []
for pos in shuffle_key:
    latinUpperShuffled.append(latinUppercaseGlyphs[pos])
    latinLowerShuffled.append(latinLowercaseGlyphs[pos])
print(latinUpperShuffled)
print(latinLowerShuffled)

#rewrite group data

#uppercase
startPos = startCharCodes.index(65)
endPos = startCharCodes.index(90+1)
charRange = range(65, 90+1)
startCharCodes = startCharCodes[:startPos] + charRange + startCharCodes[endPos:]
endCharCodes = endCharCodes[:startPos] + charRange + endCharCodes[endPos:]
startGlyphCodes = startGlyphCodes[:startPos] + latinUpperShuffled + startGlyphCodes[endPos:]

#lowercase
startPos = startCharCodes.index(97)
endPos = startCharCodes.index(122+1)
charRange = range(97, 122+1)
startCharCodes = startCharCodes[:startPos] + charRange + startCharCodes[endPos:]
endCharCodes = endCharCodes[:startPos] + charRange + endCharCodes[endPos:]
startGlyphCodes = startGlyphCodes[:startPos] + latinLowerShuffled + startGlyphCodes[endPos:]

#format 4 is obnoxious to work with, and seemingly unnecessary
#our new cmap table will only include a format 12 table, so we might as well just completely rewrite it

new_cmap_table = cmap_table[0:2] #version number
new_cmap_table += struct.pack(">H", 2) #num subtables

new_cmap_table += struct.pack(">H", 0) #unicode
new_cmap_table += struct.pack(">H", 4) #unicode 2.0+
new_cmap_table += struct.pack(">I", 20) #offset (4 + 8 * num subtables)

new_cmap_table += struct.pack(">H", 3) #windows
new_cmap_table += struct.pack(">H", 10) #unicode UCS-4
new_cmap_table += struct.pack(">I", 20) #offset (4 + 8 * num subtables)

#write actual subtable data
new_cmap_table += cmap12[0:0+4] #first four bytes remain the same
new_cmap12_length = len(startCharCodes) * 12 + 16 #16 byte header and 12 bytes per group
new_cmap_table += struct.pack(">I", new_cmap12_length) #write length
new_cmap_table += cmap12[8:8+4] #these bytes remain the same
new_cmap_table += struct.pack(">I", len(startCharCodes)) #nGroups

#write group data
for i in range(0, len(startCharCodes)):
    new_cmap_table += struct.pack(">I", startCharCodes[i])
    new_cmap_table += struct.pack(">I", endCharCodes[i])
    new_cmap_table += struct.pack(">I", startGlyphCodes[i])

#replace in memory
tableMemory[cmap_index] = new_cmap_table


# In[12]:


#The offset subtable (the first table) should not have to change at all as the number of tables remains constant
#The table directory, however, will have to change as the checkSums, offsets, and lengths of some tables will change


# In[13]:


#debug
if "of" in globals().keys():
    of.close()
    print("File Reloaded!")

out_file_name = "randomized.ttf"
of = open(out_file_name, "w+")


# In[14]:


def writeObject(object_type, obj):
    if object_type == "uint32":
        of.write(struct.pack(">I", obj))
    elif object_type == "uint16":
        of.write(struct.pack(">H", obj))
    elif object_type == "uint8":
        of.write(struct.pack(">B", obj))
    elif object_type == "formal_tag":
        for i in range(0, 4):
            writeObject("uint16", obj[i])
    elif object_type == "informal_tag":
        for i in range(0, 4):
            writeObject("uint8", ord(obj[i]))
    else:
        raise ValueError("Type Not Understood")


# In[15]:


#offset subtable
writeObject("uint32", 0x00010000)
writeObject("uint16", numTables)
writeObject("uint16", searchRange)
writeObject("uint16", entrySelector)
writeObject("uint16", rangeShift)


# In[16]:


def calcCheckSum(tableData):
    sum = 0
    for i in range(0, (len(tableData) + 3) / 4):
    #for i in range(0, (lengths[5] + 3) / 4):
        sum += struct.unpack(">I", tableData[i*4:i*4+4])[0]
    return sum % 4294967296


# In[17]:


#set checkSumAdjustment to 0 in tableMemory
head_index = tags.index("head")
head = tableMemory[head_index][:]
print(struct.unpack(">I", head[8:12])[0])
head = head[0:8] + struct.pack(">I", 0) + head[12:]
tableMemory[head_index] = head

#record new table lengths and pad tables
newLengths = []
for i in range(0, numTables):
    newLengths.append(len(tableMemory[i]))
    while len(tableMemory[i]) % 4 != 0:
        tableMemory[i] += struct.pack(">B", 0)

#Iterate Tables
offsetAddresses = []
for i in range(0, numTables):
    #tag
    writeObject("informal_tag", tags[i])
    #checkSum (calculated via the function)
    writeObject("uint32", calcCheckSum(tableMemory[i]))
    #offset (to be filled in later)
    offsetAddresses.append(of.tell())
    writeObject("uint32", 0)
    #length (not padded, though the tables in memory are padded by up to 3 bytes)
    writeObject("uint32", newLengths[i])
    #temp_table = tableMemory[i][:]
    #while struct.unpack(">B", temp_table[-1:])[0] == 0 and len(temp_table) >= len(tableMemory[i]) - 2:
    #    print(i)
    #    temp_table = temp_table[:-1]
    #writeObject("uint32", len(temp_table))


# In[18]:


sortedOffsets = sorted(offsets)
sortedIndices = []
for i in range(0, len(sortedOffsets)):
    sortedIndices.append(offsets.index(sortedOffsets[i]))
print(sortedIndices)


# In[19]:


newHeadOffset = 0
for i in sortedIndices:
    #save current offset
    current_offset = of.tell()
    if tags[i] == "head":
        newHeadOffset = current_offset
    #go back and fill in offset in table directory table
    of.seek(offsetAddresses[i])
    writeObject("uint32", current_offset)
    #return to the offset for the table to be written to
    of.seek(current_offset)
    #write table
    of.write(tableMemory[i])
newFileLength = of.tell()


# In[20]:


#calculate checkSumAdjustment
of.seek(0)
sum = 0
for i in range(0, newFileLength / 4):
    sum += struct.unpack(">I", of.read(4))[0]
checkSumAdjustment = (0xB1B0AFBA - sum) % 4294967296
print(checkSumAdjustment)
#write checkSumAdjustment
of.seek(newHeadOffset + 8)
writeObject("uint32", checkSumAdjustment)


# In[21]:


#close file
of.close()






