from enum import Enum, auto, IntFlag, Flag


class Category(str, Enum):
    ANC = "Australian New Zealand Cup"
    AWG = "Asian Winter Games"
    CAR = "Carving"
    CHI = "Children"
    CISM = "Military and Police"
    CIT = "CIT"
    CITWC = "CIT Arnold Lunn World Cup"
    COM = "World Cup Speed Event"
    CORP = "Corporate"
    DAR = "Disabled Athletes Events"
    EC = "European Cup"
    ECOM = "European Cup Speed Event"
    ENL = "Entry League FIS"
    EQUA = "European Cup Qualification"
    EXI = "Exibition"
    EYOF = "European Youth Olympic Festival"
    FEC = "Far East Cup"
    FIS = "FIS"
    FQUA = "FIS Qualification"
    JUN = "Junior"
    NAC = "Nor-Am Cup"
    NC = "National Championships"
    NGP = "Nation Grand Prix"
    NJC = "National Junior Championships"
    NJR = "National Junior Race"
    OWG = "Olympic Winter Games"
    PARA = "Para Events"
    SAC = "South American Cup"
    TRA = "Training"
    UNI = "University"
    UVS = "Universiade"
    WC = "World Cup"
    WJC = "FIS Junior World Ski Championships"
    WQUA = "World Cup Qualification"
    WSC = "FIS World Ski Championships"
    YOG = "Youth Olympic Winter Games"

    def __str__(self) -> str:
        return self.name


class Country(str, Enum):
    AFG = "Afghanistan"
    ALB = "Albania"
    DZA = "Algeria"
    AND = "Andorra"
    AGO = "Angola"
    AIA = "Anguilla"
    ARG = "Argentina"
    ARM = "Armenia"
    AUS = "Australia"
    AUT = "Austria"
    AZE = "Azerbaijan"
    BHR = "Bahrain"
    BGD = "Bangladesh"
    BLR = "Belarus"
    BEL = "Belgium"
    BTN = "Bhutan"
    BIH = "Bosnia and Herzegovina"
    BRA = "Brazil"
    BGR = "Bulgaria"
    BFA = "Burkina Faso"
    BDI = "Burundi"
    CAN = "Canada"
    CHL = "Chile"
    CHN = "China"
    HRV = "Croatia"
    CZE = "Czechia"
    DNK = "Denmark"
    EST = "Estonia"
    FRO = "Faroe Islands"
    FIN = "Finland"
    FRA = "France"
    GEO = "Georgia"
    DEU = "Germany"
    GRC = "Greece"
    HKG = "Hong Kong"
    ISL = "Iceland"
    IND = "India"
    IRN = "Iran"
    IRQ = "Iraq"
    IRL = "Ireland"
    ISR = "Israel"
    ITA = "Italy"
    JPN = "Japan"
    KAZ = "Kazakhstan"
    PRK = "North Korea"
    KOR = "South Korea"
    XKX = "Kosovo"
    KWT = "Kuwait"
    KGZ = "Kyrgyzstan"
    LVA = "Latvia"
    LBN = "Lebanon"
    LIE = "Liechtenstein"
    LTU = "Lithuania"
    LUX = "Luxembourg"
    MKD = "North Macedonia"
    MLT = "Malta"
    MEX = "Mexico"
    MDA = "Moldova"
    MNG = "Mongolia"
    MNE = "Montenegro"
    MSR = "Montserrat"
    NPL = "Nepal"
    NLD = "Netherlands"
    NZL = "New Zealand"
    NOR = "Norway"
    PAK = "Pakistan"
    PSE = "Palestine"
    PAN = "Panama"
    PER = "Peru"
    PHL = "Philippines"
    POL = "Poland"
    PRT = "Portugal"
    ROU = "Romania"
    RUS = "Russia"
    SMR = "San Marino"
    SRB = "Serbia"
    SGP = "Singapore"
    SVK = "Slovakia"
    SVN = "Slovenia"
    ZAF = "South Africa"
    ESP = "Spain"
    SWE = "Sweden"
    SUI = "Switzerland"
    SYR = "Syria"
    TWN = "Taiwan"
    TJK = "Tajikistan"
    UKR = "Ukraine"
    GBR = "United Kingdom"
    USA = "United States of America"
    UZB = "Uzbekistan"
    VNM = "Vietnam"

    def __str__(self) -> str:
        return self.name


class Discipline(str, Enum):
    AL = "Alpine Skiing"
    CC = "Cross-Country"
    FS = "Freestyle"
    GS = "Grass Skiing"
    JP = "Ski Jumping"
    MA = "Masters"
    NK = "Nordic Combined"
    SB = "Snowboard"
    SS = "Speed Skiing"
    TM = "Telemark"

    def __str__(self) -> str:
        return self.name


class Event(str, Enum):
    SL = "Slalom"
    GS = "Giant Slalom"
    SG = "Super G"
    DH = "Downhill"
    AC = "Alpine combined"
    PAR = "Parallel"
    PSL = "Parallel Slalom"
    PGS = "Parallel Giant Slalom"
    TP = "Team Parallel"


class Gender(IntFlag):
    M = auto()
    W = auto()
    All = M | W

    def __str__(self) -> str:
        return "" if self.name == "All" else self.name


class Status(IntFlag):
    ResultsAvailable = auto()
    PDFAvailable = auto()
    CheckChanges = auto()
    Cancelled = auto()
