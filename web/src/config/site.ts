export type SiteConfig = typeof siteConfig;

export const siteConfig = {
  name: 'GachaClock',
  description: '卡池时间与历史维护工具',
  navItems: [
    {
      label: "当前卡池",
      href: "/",
    },
    {
      label: "手动维护",
      href: "/manual",
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
    {
      label: "手动维护",
      href: "/manual",
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
