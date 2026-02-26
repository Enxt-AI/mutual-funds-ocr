/**
 * AMC Logo Mapping
 * Maps amc_slug patterns to the logo filename in /logos/
 * The keys are matched as partial prefixes against the actual amc_slug,
 * so "helios" matches "helios-mutual-fund", "helios-mf", etc.
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

// Sort keys by length descending so longer (more specific) keys match first
// e.g. "icici-prudential" matches before "iti"
const SORTED_KEYS = Object.keys(AMC_LOGO_MAP).sort((a, b) => b.length - a.length);

/**
 * Get the logo URL for a given AMC slug.
 * Uses prefix matching so "helios-mutual-fund" matches the "helios" key.
 * Returns the path for use in <img src="...">.
 * Falls back to null if no logo mapping exists.
 */
export function getAmcLogoUrl(amcSlug) {
    if (!amcSlug) return null;
    const slug = amcSlug.toLowerCase();

    // Try exact match first (fastest)
    if (AMC_LOGO_MAP[slug]) {
        return `/logos/${encodeURIComponent(AMC_LOGO_MAP[slug])}`;
    }

    // Try prefix matching — check if slug starts with any map key
    for (const key of SORTED_KEYS) {
        if (slug.startsWith(key) || slug.includes(key)) {
            return `/logos/${encodeURIComponent(AMC_LOGO_MAP[key])}`;
        }
    }

    return null;
}

/**
 * Get the first letter of an AMC name as fallback.
 */
export function getAmcInitial(amcName) {
    if (!amcName) return "?";
    return amcName.charAt(0).toUpperCase();
}
