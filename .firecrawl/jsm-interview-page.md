import Agent from "@/components/Agent";
import { getCurrentUser } from "@/lib/actions/auth.action";

const Page = async () => {
 const user = await getCurrentUser();

 return (
 <>


### Interview generation


 );
};

export default Page;