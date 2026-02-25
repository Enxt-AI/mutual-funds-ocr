/**
 * AMC Logo Mapping
 * Maps amc_slug to the logo filename in /logos/
 */
const AMC_LOGO_MAP = {
    "360-one": "360 ONE Mutual Fund.webp",
    "aditya-birla": "Aditya Birla Sun Life MF.webp",
    "angel-one": "Angel One Mutual Fund.svg",
    "axis": "Axis Mutual Fund.svg",
    "bajaj": "Bajaj Finserv AMC.svg",
    "bandhan": "Bandhan Mutual Fund.svg",
    "baroda-bnp-paribas": "Baroda BNP Paribas MF.svg",
    "canara-robeco": "Canara Robeco MF.svg",
    "capitalmind": "Capitalmind MF.svg",
    "choice": "Choice Mutual Fund.webp",
    "dsp": "DSP Mutual Fund.svg",
    "edelweiss": "Edelweiss Mutual Fund.svg",
    "franklin-templeton": "Franklin Templeton MF.svg",
    "groww": "Groww Mutual Fund.svg",
    "hsbc": "HSBC Mutual Fund.webp",
    "helios": "Helios Mutual Fund.svg",
    "icici-prudential": "ICICI Prudential MF.webp",
    "iti": "ITI Mutual Fund.svg",
    "invesco": "Invesco Mutual Fund.svg",
    "jm-financial": "JM Financial Mutual Fund.svg",
    "jio-blackrock": "Jio BlackRock Mutual Fund.svg",
    "kotak": "Kotak Mutual Fund.svg",
    "lic": "LIC Mutual Fund.svg",
    "mahindra-manulife": "Mahindra Manulife MF.svg",
    "mirae-asset": "Mirae Asset Mutual Fund.svg",
    "nj": "NJ Mutual Fund.svg",
    "navi": "Navi Mutual Fund.webp",
    "nippon-india": "Nippon India Mutual Fund.webp",
    "old-bridge": "Old Bridge Mutual Fund.webp",
    "pgim-india": "PGIM India Mutual Fund.svg",
    "ppfas": "PPFAS Mutual Fund.webp",
    "quant": "Quant Mutual Fund.svg",
    "quantum": "Quantum Mutual Fund.svg",
    "sbi": "SBI Mutual Fund.svg",
    "samco": "Samco Mutual Fund.svg",
    "shriram": "Shriram Mutual Fund.svg",
    "sundaram": "Sundaram Mutual Fund.svg",
    "tata": "Tata Mutual Fund.svg",
    "taurus": "Taurus Mutual Fund.svg",
    "trust": "Trust Mutual Fund.svg",
    "uti": "UTI Mutual Fund.svg",
    "unifi": "Unifi Mutual Fund.svg",
    "wealth-company": "Wealth Company AMC.webp",
    "whiteoak-capital": "WhiteOak Capital AMC.svg",
    "zerodha": "Zerodha Fund House.svg",
};

/**
 * Get the logo URL for a given AMC slug.
 * Returns the path for use in <img src="...">.
 * Falls back to null if no logo mapping exists.
 */
export function getAmcLogoUrl(amcSlug) {
    if (!amcSlug) return null;
    const filename = AMC_LOGO_MAP[amcSlug];
    if (!filename) return null;
    return `/logos/${encodeURIComponent(filename)}`;
}

/**
 * Get the first letter of an AMC name as fallback.
 */
export function getAmcInitial(amcName) {
    if (!amcName) return "?";
    return amcName.charAt(0).toUpperCase();
}
