import { Space_Grotesk, Onest } from "next/font/google";

  const onest = Onest({
    subsets: ['latin'],
    display: 'swap',
    variable: '--font-onest',
    weight: ['400', '500', '600', '700', '800', '900']
  });


const calSans = Space_Grotesk({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-cal-sans",
  weight: ["400", "500", "700"],
});

export { calSans, onest };
