export type SiteConfig = typeof siteConfig;

export const siteConfig = {
  name: 'GachaClock',
  description: '卡池时间与历史维护工具',
  navItems: [
    {
      label: "当前卡池",
      href: "/",
    },
    // {
    //   label: "Pricing",
    //   href: "/pricing",
    // },
    // {
    //   label: "Blog",
    //   href: "/blog",
    // },
    // {
    //   label: "About",
    //   href: "/about",
    // },
  ],
  navMenuItems: [
    {
      label: "当前卡池",
      href: "/",
    },
  ],
  links: {
    github: 'https://github.com/iaoongin/GachaClock',
    twitter: '',
    docs: '',
    discord: '',
    sponsor: '',
  },
};
