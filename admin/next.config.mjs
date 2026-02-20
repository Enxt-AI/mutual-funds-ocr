/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    experimental: {
        serverActions: true,
    },
    api: {
        bodyParser: {
            sizeLimit: "100mb",
        },
    },
};

export default nextConfig;
