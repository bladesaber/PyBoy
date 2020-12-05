from array import array
from . import lcd

# Palette memory = 4 colors of 2 bytes define colors for a palette, 8 different palettes
PALETTE_MEM_SIZE = 0x40
PALETTE_MEM_MAX_INDEX = 0x3f


class cgbLCD(lcd.LCD):
    def __init__(self):
        lcd.LCD.__init__(self)
        self.VRAM1 = array("B", [0] * lcd.VBANK_SIZE)

        self.sprite_palette_mem = array("I", [0xFF] * PALETTE_MEM_SIZE)
        self.bg_palette_mem = array("I", [0xFF] * PALETTE_MEM_SIZE)

        self.vbk = VBKregister()
        self.bcps = PaletteIndexRegister()
        self.bcpd = PaletteColorRegister(self.bg_palette_mem, self.bcps)
        self.ocps = PaletteIndexRegister()
        self.ocpd = PaletteColorRegister(self.sprite_palette_mem, self.ocps)

    def setVRAM(self, i, value):
        if self.vbk.active_bank == 0:
            self.VRAM0[i - 0x8000] = value
        else:
            self.VRAM1[i - 0x8000] = value
    
    def getVRAM(self, i):
        if self.vbk.active_bank == 0:
            return self.VRAM0[i - 0x8000]
        else:
            return self.VRAM1[i - 0x8000]

    #TEMPORARY FIX USED IN RENDERER.PY REMOVE THIS
    def NoOffsetgetVRAM(self, i):
        if self.vbk.active_bank == 0:
            return self.VRAM0[i]
        else:
            return self.VRAM1[i]

    def getVBANK(self):
        return self.vbk.active_bank


class VBKregister:
    def __init__(self, value=0):
        self.active_bank = value

    def set(self, value):
        #when writing to VBK, bit 0 indicates which bank to switch to
        bank = value & 1
        self._switch_bank(bank)

    def get(self):
        #reading from this register returns current VRAM bank in bit 0, other bits = 1
        return self.active_bank | 0xFE

    def _switch_bank(self, bank):
        if bank == self.active_bank:
            return
        else:
            self.active_bank = bank

class PaletteIndexRegister:
    def __init__(self, val = 0):
        self.value = val
        self.index = 0
        self.auto_inc = 0

    def set(self, val):
        if self.value == val:
            return

        self.value = val
        #bit 0-5 define index
        self.index = val & 0b111111
        #bit 7 define auto increment
        self.auto_inc = val & 0b10000000 

    def get(self):
        return self.value
    
    def getindex(self):
        return self.index

    def _inc_index(self):
        #what happens if increment is set and index is at max 0x3F?
        #maybe it wraps around?
        if not self.index == PALETTE_MEM_MAX_INDEX:
            self.index += 1

    def shouldincrement(self):
        if self.auto_inc:
            self._inc_index()

class PaletteColorRegister:
    def __init__(self, palette, i_reg, val = 0):
        #self.value = val
        self.palette = palette
        self.index_reg = i_reg
        #BGP/OCP 0-7 LOOKUP UNUSED, REMOVE?
        #self.lookup = [[0] * 4 for i in range(8)]

    def set(self, val):
        self.palette[self.index_reg.getindex()] = val
        #check for autoincrement after write
        self.index_reg.shouldincrement()
    
    def get(self):
        return self.palette[self.index_reg.getindex()]
    
    def getcolor(self, paletteindex, colorindex):
        #each palette = 8 bytes or 4 colors of 2 bytes
        i = paletteindex * 8 + colorindex * 2
        byte1 = self.palette[i] 
        byte2 = self.palette[i + 1]

        cgb_col = self._cgbcolor(byte1, byte2)
        return self._convertcolor(cgb_col)


### MOVE TO UTILS?
    #takes 2 bytes from palette memory and gets the cgb color
    #only first 15 bits used
    def _cgbcolor(self, byte1, byte2):
        #only care about 15 first bits
        mask = 0x7FFF
        d_byte = (byte2 << 8) | byte1
        return d_byte & mask

    #takes 15 bit cgb color and converts to standard 24 bit color
    #shifts the individual colors and then or with 3 most sig bits
    def _convertcolor(self, color):
        #colors 5 bits
        color_mask = 0x1F

        red = color & color_mask
        sig_bits = red & 0x07  
        final_red = (red << 3) | sig_bits
        
        green = (color >> 5) & color_mask
        sig_bits = green & 0x07  
        final_green = (green << 3) | sig_bits

        blue = (color >> 10) & color_mask
        sig_bits = blue & 0x07  
        final_blue = (blue << 3) | sig_bits
        
        return (final_red << 16) | (final_green << 8) | final_blue



#load save functions